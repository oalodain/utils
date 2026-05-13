# ciq-curl

Authenticated curl wrapper for Cisco IQ APIs. Handles login, XSRF tokens, and session cookies automatically.

## Setup

### 1. Install with uv

```bash
uv tool install ~/workspace/my-utils/ciq-curl
```

### 2. Set environment variables (add to ~/.zshrc)

```bash
export CIQ_PASSWORD='your-password-here'
```

Reload your shell (`source ~/.zshrc`) and you're done.


## Usage

```bash
ciq-curl <URL>                          # GET
ciq-curl -X POST <URL> -d '{...}'       # POST with JSON body
ciq-curl -X POST <URL> -F 'key=val'     # POST with form data
ciq-curl -X POST <URL> -F 'file=@path'  # File upload
ciq-curl -X DELETE <URL>                # DELETE
ciq-curl -v <URL>                       # Verbose (show headers)
ciq-curl -o out.json <URL>              # Save to file
ciq-curl -s <URL>                       # Silent mode
```

## examples
### simple GET call
```
ciq-curl https://ciq-rtp-dev-37-180.cx-hub-rtp.cisco.com/cxue-platform-mgr/api/v1/servers  | jq
```

### POST with json body
```
 ciq-curl -X POST /cxue-app-mgr/api/v1/apps/e03ae51f-8f88-4aba-9dee-69d442e484f9/install -d '{"instanceShortName": "default","instanceDisplayName": "Hello World","deploymentProfileName": "small"}'
```

### POST (upload a file)

```
ciq-curl -X POST /cxue-app-mgr/api/v1/apps/  -F 'file=@~/Downloads/sample-app-v1.0.16.bin'
```