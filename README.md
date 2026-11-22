# OmniDeck

<p align="center">
  <img src="https://i.pinimg.com/originals/62/78/b6/6278b6a18228dba36ec3b5b1166c23d6.jpg" width="1080" alt="OmniDeck Icon">
</p>

Bem-vindo ao **OmniDeck**, uma solução completa para utilizar seu dispositivo Android como um controle virtual ou volante para Linux, utilizando conexões WebSocket de baixa latência e emulação de input no kernel (`uinput`).

## 📌 Visão Geral
O projeto é composto de duas partes essenciais:
1. **App Mobile (Android)**: Interface construída em Kivy, capturando toques na tela e dados do giroscópio.
2. **Servidor (Linux)**: Aplicação GTK 3 nativa que roda em modo `root` (via `pkexec`) e emula um controle de Xbox 360 através do `evdev/uinput`.

## 📂 Estrutura do Projeto
A base de código foi refatorada e organizada de forma modular para fácil manutenção.

- `app/`
  - `main.py`
  - `__init__.py`
  - `ui_components.py`
  - `screens.py`
- `server/`
  - `main-server.py`
  - `__init__.py`
  - `core.py`
- `assets/images/`
- `build/`
  - `build-app.sh`

## ⚙️ Requisitos e Dependências

O projeto usa **`uv`** para gerenciar as dependências Python. A interface do servidor usa GTK 3 e os pacotes do sistema, sem instalar bindings Qt ou empacotar uma toolkit gráfica via pip.

### Dependências do Sistema (Linux)
O servidor requer GTK 3, PyGObject, `evdev` e `websockets`. No Debian/Ubuntu, instale os pacotes do sistema:
```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0 python3-evdev python3-websockets policykit-1
```

## 🚀 Build e Execução

**1. Configurar o Ambiente Virtual (usando `uv`)**
Para desenvolver o app Android, crie o ambiente com as dependências opcionais do app e as ferramentas de build:
```bash
uv sync --extra app --group android
```

**2. Rodar o App Mobile**
```bash
uv run --extra app app/main.py
```

**3. Rodar o Servidor**
```bash
uv run --no-project --python /usr/bin/python3 server/main-server.py
```

O comando usa o Python do sistema para que o servidor encontre o GTK instalado pelo `apt` (`gi` não é um pacote PyPI). Ele solicita elevação via `pkexec`. Para usar somente o servidor, `uv sync` instala apenas `evdev` e `websockets`; a interface GTK 3 permanece fornecida pelos pacotes do sistema.

**4. Gerar as Builds**
- App Android (gera `OmniDeck.apk`): `bash build/build-app.sh`
- Servidor Debian: `bash build/build-server.sh`
