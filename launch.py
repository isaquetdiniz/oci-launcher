#!/usr/bin/env python3
"""
Fica tentando criar uma instância ARM Always Free na Oracle Cloud
até conseguir capacidade disponível.

Pré-requisitos:
  pip install oci
  ~/.oci/config configurado (gerado via: oci setup config)

Como obter SUBNET_ID e IMAGE_ID:
  1. Console OCI → Compute → Instances → Create Instance
  2. Seleciona Ubuntu + Shape A1 Flex
  3. Abre DevTools (F12) → aba Network
  4. Clica em Create (vai dar Out of Capacity)
  5. Acha a requisição POST /instances em vermelho
  6. Copia o payload e extrai subnetId e imageId
"""

import oci
import time
import sys
from datetime import datetime

# ── Configure aqui ────────────────────────────────────────────

SUBNET_ID           = ""   # ocid1.subnet.oc1.<region>.aaaa...
IMAGE_ID            = ""   # ocid1.image.oc1.<region>.aaaa...
SSH_PUBLIC_KEY      = ""   # ssh-rsa AAAA...

OCPUS               = 4
MEMORY_IN_GBS       = 24
BOOT_VOLUME_GB      = 50
DISPLAY_NAME        = "themachine"
AVAILABILITY_DOMAIN = ""   # Ex: "LiZf:SA-SAOPAULO-1-AD-1"
RETRY_SECS          = 60

# ─────────────────────────────────────────────────────────────


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    if not all([SUBNET_ID, IMAGE_ID, SSH_PUBLIC_KEY]):
        print("Preencha SUBNET_ID, IMAGE_ID e SSH_PUBLIC_KEY no script.")
        sys.exit(1)

    config     = oci.config.from_file()
    compute    = oci.core.ComputeClient(config)
    tenancy_id = config["tenancy"]

    log(f"Availability domain: {AVAILABILITY_DOMAIN}")

    # Verifica se instância já existe
    instances = compute.list_instances(tenancy_id).data
    for i in instances:
        if i.display_name == DISPLAY_NAME and i.lifecycle_state not in ("TERMINATED", "TERMINATING"):
            log(f"Instância '{DISPLAY_NAME}' já existe ({i.lifecycle_state}). Encerrando.")
            sys.exit(0)

    details = oci.core.models.LaunchInstanceDetails(
        compartment_id=tenancy_id,
        availability_domain=AVAILABILITY_DOMAIN,
        display_name=DISPLAY_NAME,
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=OCPUS,
            memory_in_gbs=MEMORY_IN_GBS,
        ),
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            source_type="image",
            image_id=IMAGE_ID,
            boot_volume_size_in_gbs=BOOT_VOLUME_GB,
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=SUBNET_ID,
            assign_public_ip=True,
        ),
        metadata={"ssh_authorized_keys": SSH_PUBLIC_KEY},
    )

    attempt = 0
    while True:
        attempt += 1
        try:
            log(f"Tentativa #{attempt}...")
            response = compute.launch_instance(details)
            instance_id = response.data.id
            log(f"Instância criada! OCID: {instance_id}")

            # Aguarda o IP público ficar disponível
            vnet = oci.core.VirtualNetworkClient(config)
            log("Aguardando IP público...")
            for _ in range(30):
                time.sleep(10)
                attachments = compute.list_vnic_attachments(tenancy_id, instance_id=instance_id).data
                if attachments:
                    vnic = vnet.get_vnic(attachments[0].vnic_id).data
                    if vnic.public_ip:
                        log(f"Pronto! IP: {vnic.public_ip}")
                        log(f"Acesse: ssh ubuntu@{vnic.public_ip}")
                        sys.exit(0)

            log("Instância criada, mas IP ainda não disponível. Verifique no console.")
            sys.exit(0)

        except oci.exceptions.ServiceError as e:
            if "Out of host capacity" in (e.message or ""):
                log(f"Sem capacidade. Próxima tentativa em {RETRY_SECS}s...")
                time.sleep(RETRY_SECS)
            elif e.status == 429:
                wait = RETRY_SECS * 2
                log(f"Rate limit. Aguardando {wait}s...")
                time.sleep(wait)
            else:
                log(f"Erro inesperado ({e.status}): {e.message}")
                log(f"Detalhes: {e}")
                sys.exit(1)
        except Exception as e:
            log(f"Erro de conexão: {e}. Próxima tentativa em {RETRY_SECS}s...")
            time.sleep(RETRY_SECS)


if __name__ == "__main__":
    main()
