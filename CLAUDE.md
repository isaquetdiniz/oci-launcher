# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

Script Python que fica tentando provisionar uma instância ARM Always Free na Oracle Cloud (shape `VM.Standard.A1.Flex`) até que haja capacidade disponível no availability domain configurado.

## Dependência

```bash
pip install oci
```

A autenticação usa `~/.oci/config` (gerado via `oci setup config`).

## Como executar

```bash
python launch.py
```

O script roda em loop infinito até criar a instância ou encontrar um erro não-recuperável. Para rodar em background e persistir além da sessão SSH:

```bash
nohup python launch.py >> oci.log 2>&1 &
```

## Arquitetura

`launch.py` é um script single-file com três etapas sequenciais:

1. **Verificação de existência** — usa `ComputeClient.list_instances()` para evitar duplicatas pelo `DISPLAY_NAME`.
2. **Loop de criação** — chama `ComputeClient.launch_instance()` em retry; trata `Out of host capacity` (espera `RETRY_SECS`) e HTTP 429 (espera `RETRY_SECS * 2`).
3. **Aguardo de IP** — após criar, polling em `list_vnic_attachments` + `get_vnic` até o IP público aparecer.

## Configuração (topo de `launch.py`)

| Variável | Descrição |
|---|---|
| `SUBNET_ID` | OCID da subnet (extraído do DevTools no console OCI) |
| `IMAGE_ID` | OCID da imagem Ubuntu (extraído do DevTools) |
| `SSH_PUBLIC_KEY` | Chave pública SSH para acesso à instância |
| `OCPUS` / `MEMORY_IN_GBS` | Recursos do shape A1 Flex (máx. 4 OCPUs / 24 GB no Always Free) |
| `AVAILABILITY_DOMAIN` | AD da região (ex: `LiZf:SA-SAOPAULO-1-AD-1`) |
| `RETRY_SECS` | Intervalo entre tentativas (padrão: 60s) |

## Pós-criação

`SETUP.md` contém o guia de hardening da instância após o provisionamento: atualizações, UFW, Fail2ban, usuário dedicado, configuração SSH, Docker.
