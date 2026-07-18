# Deploy Checklist - cassellas-api

## 1) Deploy e validacao em HML (AWS)
- [ ] Rodar workflow `Pipeline` com `deploy=true`
- [ ] Validar rollout no cluster AWS (`kubectl rollout status deployment/cassellas-api -n cassellas-api`)
- [ ] `curl -i https://hml-api.cassellas.com.br/`
- [ ] `curl -i https://hml-api.cassellas.com.br/now`
- [ ] `curl -i https://hml-api.cassellas.com.br/API/cassellas-api/now`

## 2) Aprovar promocao para producao
- [ ] Revisar evidencias de HML (healthcheck, logs, regressao)
- [ ] Aprovar no environment `gcp-prod` no GitHub Actions

## 3) Validar saude da API em producao (GCP)
- [ ] `curl -i https://api.cassellas.com.br/`
- [ ] `curl -i https://api.cassellas.com.br/now`
- [ ] `curl -i https://api.cassellas.com.br/API/cassellas-api/now`

## 4) Validar certificado TLS em producao (GCP)
- [ ] `kubectl get managedcertificate cassellas-api-cert-v2 -n cassellas-api -w`
- [ ] Confirmar status `Active`
- [ ] `curl -i https://api.cassellas.com.br/now`

## 5) Revisar DNS
- [ ] `hml-api.cassellas.com.br` apontando para o Ingress de HML (AWS)
- [ ] `api.cassellas.com.br` apontando para o Ingress de producao (GCP)
- [ ] Se usar Cloudflare, manter sem proxy ate estabilizar TLS
- [ ] Verificar CAA (se existir)

## 6) Padronizar tags de imagem
- [ ] Nao usar `latest` em producao
- [ ] Usar tag imutavel (commit SHA ou release tag)
- [ ] Registrar imagem exata implantada

## 7) Pipeline de deploy
- [ ] Validar sequencia: HML AWS -> aprovacao -> Producao GCP
- [ ] Validar job de HML usando contexto correto (`AWS_HML_KUBE_CONTEXT` quando aplicavel)
- [ ] Validar bloqueio de aprovacao no environment `gcp-prod`

## 8) Permissoes minimas
- [ ] Garantir permissao de pull para nodes do GKE
- [ ] Garantir permissao de pull para nodes do cluster AWS de HML
- [ ] Revisar roles e remover excesso
- [ ] Documentar roles obrigatorias

## 9) Reproducibilidade e rollback
- [ ] Documentar comando de release
- [ ] Documentar comando de rollback para imagem anterior
- [ ] Definir timeout padrao de rollout

## 10) Monitoramento basico
- [ ] Alertar `ImagePullBackOff`
- [ ] Alertar `deployment unavailable`
- [ ] Alertar certificado em `Provisioning` por muito tempo

## 11) Integracao com front-end
- [ ] Front HML usando `https://hml-api.cassellas.com.br`
- [ ] Front producao usando `https://api.cassellas.com.br`
- [ ] Ajustar URL final da API no front-end
- [ ] Validar CORS e headers
- [ ] Validar ausencia de mixed content

## 12) Limpeza final
- [ ] Remover recursos temporarios
- [ ] Validar ReplicaSets/pods esperados
- [ ] Registrar versao final implantada (imagem, data, responsavel)
