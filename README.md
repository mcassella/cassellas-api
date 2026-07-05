# cassellas-api

API FastAPI preparada para build em `ghcr.io` e deploy em GKE com GitHub Actions.

## Estrutura

- `main.py`: app FastAPI com endpoints `/` e `/healthz`
- `Dockerfile`: imagem de produção com `uvicorn`
- `.github/workflows/deploy.yml`: build da imagem no GHCR e deploy no GKE
- `k8s/`: manifests base e overlay de produção

## Repositório GitHub

Como o ambiente atual nao tem `gh` nem token GitHub configurado, a criacao do repositório remoto precisa ser feita por voce em um destes caminhos:

1. Via interface web: crie `mcassella/cassellas-api` sem `README`, `.gitignore` ou license.
2. Via GitHub CLI em uma maquina com `gh` autenticado:

```bash
gh repo create mcassella/cassellas-api --public --source . --remote origin --push
```

Depois que o repo existir, configure o remoto local e faça o primeiro push:

```bash
git remote add origin git@github.com:mcassella/cassellas-api.git
git add .
git commit -m "chore: bootstrap FastAPI API and GKE deploy pipeline"
git push -u origin main
```

## GHCR

O workflow publica a imagem em `ghcr.io/mcassella/cassellas-api` usando o `GITHUB_TOKEN` nativo do Actions. Nao e necessario PAT para esse fluxo, desde que o push ocorra no proprio repo do GitHub.

## Variaveis e secrets do GitHub Actions

Defina estes `Repository variables`:

- `GCP_PROJECT_ID`
- `GKE_CLUSTER`
- `GKE_LOCATION`

Defina estes `Repository secrets`:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`

## GCP / GKE

1. Crie um service account com permissao para atualizar recursos no cluster.
2. Configure Workload Identity Federation ligando o repo GitHub ao provider do GCP.
3. Instale no cluster o suporte ao `ManagedCertificate` e ao Ingress GCE, se ainda nao estiver ativo.
4. Depois do primeiro deploy, obtenha o IP do Ingress e aponte o DNS `api.cassellas.com.br` para ele.

Comandos uteis:

```bash
kubectl get ingress -n cassellas-api
kubectl get managedcertificate -n cassellas-api
kubectl get deploy,svc,pods -n cassellas-api
```

## Execucao local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```