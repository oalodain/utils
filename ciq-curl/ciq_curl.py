"""Authenticated curl wrapper for Cisco IQ APIs.

Handles login, XSRF token rotation, and session cookies automatically.
Password is read from the CIQ_PASSWORD environment variable.

Usage:
    # GET request
    ciq-curl https://host/cxue-app-mgr/api/v1/apps

    # POST with JSON body
    ciq-curl -X POST https://host/cxue-app-mgr/api/v1/apps/ID/install/ \\
        -d '{"deploymentProfileName": "small"}'

    # POST with form data
    ciq-curl -X POST https://host/cxue-app-mgr/api/v1/apps/ \\
        --form 'serverId=UUID' --form 'filename=app.tar.zstd'

    # File upload (use @path like curl)
    ciq-curl -X POST https://host/cxue-app-mgr/api/v1/apps/ \\
        -F 'file=@/path/to/myapp-v1.0.0.tar.zstd'

    # DELETE
    ciq-curl -X DELETE https://host/cxue-app-mgr/api/v1/apps/ID/

    # Custom headers
    ciq-curl -H 'Accept: text/plain' https://host/path

    # Verbose mode (show request/response headers)
    ciq-curl -v https://host/path

    # Disable TLS verification (like curl -k)
    ciq-curl -k https://host/path

    # Output to file (like curl -o)
    ciq-curl -o output.json https://host/path

    # Load cookies from JSON file
    ciq-curl --cookies cookies.json https://host/path
"""

import argparse
import json
import os
import sys
from typing import IO
from urllib.parse import urlparse
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CIQSession:
    """Manages authentication and XSRF tokens for Cisco IQ APIs."""

    def __init__(self, base_url: str, *, verify: bool = True, cookies_file: str | None = None, skip_auth: bool = False):
        self.base_url = base_url.rstrip("/")
        self.verify = verify
        self.session = requests.Session()
        self.session.verify = verify
        self._authenticated = False
        self.skip_auth = skip_auth
        if cookies_file:
            self._load_cookies(cookies_file)

    def _load_cookies(self, cookies_file: str) -> None:
        """Load cookies from a JSON file into the session."""
        try:
            with open(cookies_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading cookies file: {e}", file=sys.stderr)
            sys.exit(1)

        # Extract cookies from the "Request Cookies" object, or use top-level if it's a flat dict
        cookies_data = data.get("Request Cookies", data)
        
        if not isinstance(cookies_data, dict):
            print("Error: cookies file must contain a dict or 'Request Cookies' object", file=sys.stderr)
            sys.exit(1)

        for key, value in cookies_data.items():
            self.session.cookies.set(key, value)

    def _login(self) -> None:
        password = os.environ.get("CIQ_PASSWORD")
        if not password:
            print("Error: CIQ_PASSWORD environment variable is not set.", file=sys.stderr)
            sys.exit(1)

        resp = self.session.post(
            f"{self.base_url}/cxp-iam/api/v1/auth/login",
            json={"email": "admin", "secret": password},
        )
        if resp.status_code >= 400:
            print(f"Login failed ({resp.status_code}): {resp.text}", file=sys.stderr)
            sys.exit(1)

        self._authenticated = True

    def _ensure_auth(self) -> None:
        if not self._authenticated and not self.skip_auth:
            self._login()

    def _inject_xsrf(self, method: str) -> dict[str, str]:
        """Return XSRF header dict for mutating methods."""
        if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            token = self.session.cookies.get("X-XSRF-TOKEN")
            # Refresh token only when missing.
            if not token:
                try:
                    self.session.get(f"{self.base_url}/cxue-platform-mgr/api/v1/system/version")
                except requests.RequestException:
                    pass
                token = self.session.cookies.get("X-XSRF-TOKEN")
            if token:
                return {"X-XSRF-TOKEN": token}
        return {}

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: str | None = None,
        form_data: dict[str, str] | None = None,
        files: dict | None = None,
    ) -> requests.Response:
        self._ensure_auth()

        req_headers = {**self._inject_xsrf(method), **(headers or {})}

        kwargs: dict = {"headers": req_headers}
        if files:
            kwargs["files"] = files
            if form_data:
                kwargs["data"] = form_data
        elif form_data:
            kwargs["data"] = form_data
        elif data:
            # Auto-detect JSON
            try:
                json.loads(data)
                kwargs["json"] = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                kwargs["data"] = data
                req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        resp = self.session.request(method, url, **kwargs)

        # If we get a 401/403, re-authenticate once and retry (unless skip_auth is set).
        if resp.status_code in (401, 403) and self._authenticated and not self.skip_auth:
            self._authenticated = False
            self._login()
            req_headers.update(self._inject_xsrf(method))
            kwargs["headers"] = req_headers
            resp = self.session.request(method, url, **kwargs)

        return resp


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Authenticated curl wrapper for Cisco IQ APIs.",
        usage="%(prog)s [options] URL",
    )
    parser.add_argument("url", metavar="URL")
    parser.add_argument("-X", "--request", dest="method", default="GET")
    parser.add_argument("-H", "--header", dest="headers", action="append", default=[])
    parser.add_argument("-d", "--data", dest="data", default=None)
    parser.add_argument("-F", "--form", dest="form", action="append", default=[])
    parser.add_argument("-o", "--output", dest="output", default=None)
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
    parser.add_argument("-s", "--silent", dest="silent", action="store_true")
    parser.add_argument("--cookies", dest="cookies", default=None,
                        help="Path to JSON file containing cookies to inject into requests")
    parser.add_argument("--no-auth", dest="no_auth", action="store_true",
                        help="Skip authentication and use only cookies from file")

    args = parser.parse_args(argv)

    return args


def main(argv: list[str] | None = None) -> int:
    if not (argv if argv is not None else sys.argv[1:]):
        print(__doc__)
        return 0

    args = parse_args(argv)

    full_url = args.url
    if not full_url.startswith(("http://", "https://")):
        print("Error: URL must start with http:// or https://", file=sys.stderr)
        return 1

    parsed = urlparse(full_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    ciq = CIQSession(base_url, verify=False, cookies_file=args.cookies, skip_auth=args.no_auth)

    # Parse extra headers
    headers: dict[str, str] = {}
    for h in args.headers:
        if ":" not in h:
            print(f"Invalid header format (expected 'Name: Value'): {h}", file=sys.stderr)
            return 1
        name, _, value = h.partition(":")
        headers[name.strip()] = value.strip()

    # Parse form fields, separating file uploads (@path) from plain fields
    form_data: dict[str, str] | None = None
    files: dict[str, tuple[str, "IO[bytes]", str]] | None = None
    if args.form:
        form_data = {}
        for f in args.form:
            if "=" not in f:
                print(f"Invalid form field (expected 'key=value'): {f}", file=sys.stderr)
                return 1
            key, _, val = f.partition("=")
            if val.startswith("@"):
                filepath = val[1:]
                if not os.path.isfile(filepath):
                    print(f"File not found: {filepath}", file=sys.stderr)
                    return 1
                if files is None:
                    files = {}
                files[key] = (os.path.basename(filepath), open(filepath, "rb"), "application/octet-stream")
            else:
                form_data[key] = val
        if not form_data:
            form_data = None

    try:
        # Execute request
        resp = ciq.request(
            args.method,
            full_url,
            headers=headers,
            data=args.data,
            form_data=form_data,
            files=files,
        )
    finally:
        if files:
            for _, (_, fobj, _) in files.items():
                fobj.close()

    # Verbose output
    if args.verbose:
        print(f"> {args.method} {parsed.path}", file=sys.stderr)
        for k, v in resp.request.headers.items():
            print(f"> {k}: {v}", file=sys.stderr)
        print(">", file=sys.stderr)
        print(
            f"< HTTP/{resp.raw.version / 10:.1f} {resp.status_code} {resp.reason}",
            file=sys.stderr,
        )
        for k, v in resp.headers.items():
            print(f"< {k}: {v}", file=sys.stderr)
        print("<", file=sys.stderr)

    # Output
    body = resp.text
    if args.output:
        with open(args.output, "w") as f:
            f.write(body)
        if not args.silent:
            print(f"Written to {args.output}", file=sys.stderr)
    else:
        # Pretty-print JSON responses
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            try:
                parsed_json = resp.json()
                body = json.dumps(parsed_json)
            except (json.JSONDecodeError, ValueError):
                pass
        print(body)

    # Exit with non-zero on HTTP errors (like curl --fail)
    if resp.status_code >= 400:
        if not args.silent:
            print(f"HTTP {resp.status_code}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
