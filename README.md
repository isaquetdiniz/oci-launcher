# OCI ARM Launcher

Fica tentando criar uma instância **ARM Always Free** na Oracle Cloud
(`VM.Standard.A1.Flex`) até que haja capacidade disponível no availability domain.

## Pré-requisitos

- Python 3.8+
- OCI SDK: `pip install oci`
- Credenciais configuradas: `oci setup config` (gera `~/.oci/config`)

## Configuração

Edite o bloco de constantes no topo de `launch.py`:

| Variável | Como obter |
|---|---|
| `SUBNET_ID` | Console OCI → Networking → Virtual Cloud Networks → sua VCN → Subnets → copie o OCID |
| `IMAGE_ID` | Console OCI → Compute → Instances → Create Instance → selecione Ubuntu + A1 Flex → abra DevTools (F12) → aba Network → clique em Create → na requisição vermelha `POST /instances` copie o campo `imageId` do payload |
| `SSH_PUBLIC_KEY` | Conteúdo de `~/.ssh/id_rsa.pub` (ou a chave que preferir) |
| `AVAILABILITY_DOMAIN` | Console OCI → Compute → Instances → Create Instance → campo Availability Domain |
| `OCPUS` / `MEMORY_IN_GBS` | Máximo no Always Free: 4 OCPUs e 24 GB RAM |

## Executar

```bash
python launch.py
```

Para rodar em background e persistir após fechar o terminal:

```bash
nohup python launch.py >> oci.log 2>&1 &
tail -f oci.log   # acompanhar progresso
```

O script retorna assim que o IP público estiver disponível:

```
[10:23:41] Instância criada! OCID: ocid1.instance...
[10:23:41] Aguardando IP público...
[10:24:11] Pronto! IP: 123.45.67.89
[10:24:11] Acesse: ssh ubuntu@123.45.67.89
```

## Pós-provisionamento

Consulte [`SETUP.md`](SETUP.md) para hardening da instância: firewall, Fail2ban, usuário dedicado, Docker, otimizações de kernel.
