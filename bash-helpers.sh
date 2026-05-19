ssh system-orchestrator@$1 'cat >> ~/.bashrc << '\''EOF'\''

##################################################
###################### Helpers #####################
##################################################
ns() {
    kubectl config set-context --current --namespace="$1"
}
klog() {
  kubectl get pods | grep "$1" | awk '\''{print $1}'\'' | head -n 1 | xargs kubectl logs -f
}
kdelp() {
  kubectl get pods | grep "$1" | awk '\''{print $1}'\'' | head -n 1 | xargs kubectl delete po
}
app-mgr() {
  curl -X "${1^^}" http://localhost:8003/cxue-app-mgr/api/v1/$2
}
plat-mgr() {
  curl -X "${1^^}" http://localhost:8002/cxue-platform-mgr/api/v1/$2
}
sys-orch() {
  curl -X "${1^^}" http://localhost:8000/v1/$2
}


alias h="history | grep"
alias get="kubectl get all | grep $1"
alias postgres="kubectl exec -it cxue-postgres-cluster-0 -c postgres -n cxue -- psql"
alias minio="cd /cisco/data/minio/data0"
alias sample="cd /cisco/data/apps/sample-app/artifacts/"
EOF'