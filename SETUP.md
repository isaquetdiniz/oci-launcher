# OCI ARM Machine Hardening

Guia de configuração para instâncias Oracle Cloud ARM (Ampere A1).
Testado em Ubuntu 24.04 LTS.

---

## 1. Atualizar o sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip
```

---

## 2. Atualizações automáticas de segurança

```bash
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## 3. Timezone e NTP

```bash
sudo timedatectl set-timezone America/Sao_Paulo
sudo apt install chrony -y
```

---

## 4. Otimizações de kernel

Adicione ao final de `/etc/sysctl.conf`:

```
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
fs.file-max = 2097152
```

```bash
sudo sysctl -p
```

---

## 5. Swap

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## 6. Ferramentas de observabilidade

```bash
sudo apt install -y htop ncdu glances
```

- `htop` — monitor de processos interativo
- `ncdu` — análise de uso de disco
- `glances` — visão geral do sistema (CPU, RAM, rede, disco)

---

## 7. Firewall (UFW)

```bash
sudo apt install ufw -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

> Abra também as portas 80 e 443 nas **Security Lists** da VCN no console Oracle Cloud (Networking → Virtual Cloud Networks → Security Lists → Ingress Rules).

---

## 8. Fail2ban

```bash
sudo apt install fail2ban -y
sudo systemctl enable --now fail2ban
```

---

## 9. Criar usuário dedicado

Crie um novo usuário e adicione aos grupos `sudo` e `docker`:

```bash
sudo adduser seunome
sudo usermod -aG sudo,docker seunome
```

Copie a chave SSH do usuário padrão (`ubuntu`) para o novo usuário:

```bash
sudo mkdir -p /home/seunome/.ssh
sudo cp ~/.ssh/authorized_keys /home/seunome/.ssh/
sudo chown -R seunome:seunome /home/seunome/.ssh
sudo chmod 700 /home/seunome/.ssh
sudo chmod 600 /home/seunome/.ssh/authorized_keys
```

Habilite sudo sem senha:

```bash
sudo visudo
```

Adicione no final do arquivo:
```
seunome ALL=(ALL) NOPASSWD:ALL
```

**Teste o acesso em uma nova sessão SSH antes de continuar:**

```bash
ssh -i sua-chave.pem seunome@ip-da-maquina
sudo whoami  # deve retornar: root
```

---

## 10. Configurar SSH

> ⚠️ Só faça isso após confirmar o acesso com o novo usuário.

Edite `/etc/ssh/sshd_config`:

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
AllowUsers seunome
```

```bash
sudo systemctl restart ssh
```

Confirme que o usuário `ubuntu` (ou padrão) foi bloqueado tentando logar com ele — deve retornar `Permission denied`.

---

## 11. Docker

```bash
sudo apt remove docker docker-engine docker.io containerd runc -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

Crie `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "live-restore": true
}
```

```bash
sudo systemctl restart docker
docker compose version  # confirma instalação
```
