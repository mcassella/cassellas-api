# Deploy Checklist - cassellas-api

## 1) Validar saude da API em producao
- [ ] `curl -i http://api.cassellas.com.br/`
- [ ] `curl -i http://api.cassellas.com.br/now`
- [ ] `curl -i http://api.cassellas.com.br/API/cassellas-api/now`

## 2) Validar certificado TLS
- [ ] `kubectl get managedcertificate cassellas-api-cert -n cassellas-api -w`
- [ ] Confirmar status `Active`
- [ ] `curl -i https://api.cassellas.com.br/now`

## 3) Revisar DNS
- [ ] `api.cassellas.com.br` apontando para o IP do Ingress
- [ ] Se usar Cloudflare, manter sem proxy ate estabilizar TLS
- [ ] Verificar CAA (se existir)

## 4) Padronizar tags de imagem
- [ ] Nao usar `latest` em producao
- [ ] Usar tag imutavel (commit SHA ou release tag)
- [ ] Registrar imagem exata implantada

## 5) Pipeline de deploy
- [ ] Escolher fluxo unico (GitHub Actions + GHCR, ou GCP)
- [ ] Habilitar APIs necessarias (ex.: Cloud Build, se for usar)
- [ ] Validar rollout automatico no pipeline

## 6) Permissoes minimas
- [ ] Garantir permissao de pull para nodes do GKE
- [ ] Revisar roles e remover excesso
- [ ] Documentar roles obrigatorias

## 7) Reproducibilidade e rollback
- [ ] Documentar comando de release
- [ ] Documentar comando de rollback para imagem anterior
- [ ] Definir timeout padrao de rollout

## 8) Monitoramento basico
- [ ] Alertar `ImagePullBackOff`
- [ ] Alertar `deployment unavailable`
- [ ] Alertar certificado em `Provisioning` por muito tempo

## 9) Integracao com front-end (quando TLS estiver Active)
- [ ] Ajustar URL final da API no front-end
- [ ] Validar CORS e headers
- [ ] Validar ausencia de mixed content

## 10) Limpeza final
- [ ] Remover recursos temporarios
- [ ] Validar ReplicaSets/pods esperados
- [ ] Registrar versao final implantada (imagem, data, responsavel)
