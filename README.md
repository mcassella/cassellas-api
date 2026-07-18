# cassellas-api

API FastAPI preparada para build em `ghcr.io` e deploy progressivo com GitHub Actions:

1. Homologacao em cluster AWS: `https://hml-api.cassellas.com.br`
2. Producao em GCP/GKE: `https://api.cassellas.com.br`

## Autenticacao (versao inicial)

A API possui login simples por usuario e senha com validacao em arquivo TXT.

- Endpoint: `POST /auth/login`
- Endpoint com prefixo: `POST /API/{API_NAME}/auth/login`
- Body JSON:

```json
{
	"username": "admin",
	"password": "admin123"
}
```

O arquivo padrao de usuarios e `users.txt` (raiz do projeto), no formato:

```txt
usuario:senha_em_sha512_hex
```

Voce pode alterar o caminho com a variavel de ambiente `AUTH_USERS_FILE`.

Para gerar o SHA-512 de uma senha no Linux:

```bash
printf 'minha_senha' | sha512sum
```

## MFA com Microsoft Authenticator

O MFA usa TOTP (padrao compativel com Microsoft Authenticator).

Se o usuario tiver MFA configurado, o endpoint de login simples (`/auth/login`) retorna `403` e exige `/auth/login/mfa`.

- Setup do MFA: `POST /auth/mfa/setup`
- Login com MFA: `POST /auth/login/mfa`
- Versoes com prefixo:
	- `POST /API/{API_NAME}/auth/mfa/setup`
	- `POST /API/{API_NAME}/auth/login/mfa`

Arquivo de segredos MFA (padrao): `mfa_secrets.txt`, no formato:

```txt
usuario:segredo_base32
```

Pode ser alterado por `AUTH_MFA_FILE`.

### 1) Setup no Microsoft Authenticator

Chame o setup com usuario e senha validos:

```bash
curl -X POST "http://localhost:8080/auth/mfa/setup" \
	-H "Content-Type: application/json" \
	-d '{"username":"admin","password":"admin123"}'
```

A resposta retorna `secret`, `otpauth_uri` e `qr_code_png_base64` (PNG em Base64).

No app Microsoft Authenticator:
1. Adicione uma nova conta.
2. Escaneie o QR code (ou escolha entrada manual).
3. Informe o segredo (`secret`) e finalize.

Exemplo para salvar o QR em arquivo no Linux:

```bash
curl -s -X POST "http://localhost:8080/auth/mfa/setup" \
	-H "Content-Type: application/json" \
	-d '{"username":"admin","password":"admin123"}' \
| python3 -c "import sys, json, base64; d=json.load(sys.stdin); open('mfa_qr.png','wb').write(base64.b64decode(d['qr_code_png_base64']))"
```

### 2) Login com MFA

Use usuario, senha e OTP atual do app:

```bash
curl -X POST "http://localhost:8080/auth/login/mfa" \
	-H "Content-Type: application/json" \
	-d '{"username":"admin","password":"admin123","otp":"123456"}'
```

### 3) Desativar MFA

Requer senha e OTP atual. Apos desativar, o usuario volta a usar apenas `/auth/login`.

```bash
curl -X POST "http://localhost:8080/auth/mfa/disable" \
	-H "Content-Type: application/json" \
	-d '{"username":"admin","password":"admin123","otp":"123456"}'
```

## Estrutura

- `main.py`: app FastAPI com endpoints `/` e `/healthz`
- `Dockerfile`: imagem de produção com `uvicorn`
- `.github/workflows/pipeline.yml`: test/security/build, deploy em HML (AWS) e promocao para Producao (GCP)
- `k8s/`: manifests base e overlays `aws-hml`, `minikube` e `prod`

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
- `AWS_HML_KUBE_CONTEXT` (opcional, contexto `kubectl` para o cluster de HML em AWS)

Defina estes `Repository secrets`:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`

## Gate de aprovacao para producao

O workflow principal usa dois `environments`:

- `aws-hml`: deploy automatico de homologacao
- `gcp-prod`: deploy de producao

Para garantir "HML primeiro, producao depois de aprovado", configure `Required reviewers` no environment `gcp-prod` no GitHub.

## GCP / GKE

1. Crie um service account com permissao para atualizar recursos no cluster.
2. Configure Workload Identity Federation ligando o repo GitHub ao provider do GCP.
3. Instale no cluster o suporte ao `ManagedCertificate` e ao Ingress GCE, se ainda nao estiver ativo.
4. Depois do primeiro deploy, obtenha o IP do Ingress e aponte o DNS `api.cassellas.com.br` para ele.

## AWS HML

1. Garanta acesso do runner self-hosted ao cluster Kubernetes de homologacao na AWS.
2. Configure o DNS `hml-api.cassellas.com.br` para o ingress/controller desse cluster.
3. Se necessario, configure `AWS_HML_KUBE_CONTEXT` para selecionar o contexto correto no runner.

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