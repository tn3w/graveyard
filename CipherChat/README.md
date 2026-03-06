<div class="center">
    <img alt="Logo" src="https://github.com/tn3w/CipherChat/releases/download/iu/CipherChat.png">
</div>
<p align="center"><a rel="noreferrer noopener" href="http://tn3wtor4vgnrimugptubpaqsf2gc4pcsktknkxt74w7p5yzbt7rwrkid.onion/projects/CipherChat"><img alt="Backup 1" src="https://img.shields.io/badge/Backup%201-141e24.svg?&style=for-the-badge&logo=torproject&logoColor=white"></a>  <a rel="noreferrer noopener" href="http://tn3wvjimrn3hydx4u52kzfnkgu6kffef2js27ewlhdf5htulno34vqad.onion/projects/CipherChat"><img alt="Backup 2" src="https://img.shields.io/badge/Backup%202-141e24.svg?&style=for-the-badge&logo=torproject&logoColor=white"></a>  <a rel="noreferrer noopener" href="http://tn3wtor7cfz3epmuetrhkj3mangjxqpd47lxxicfwwdwja6dwq6dbdad.onion/projects/CipherChat"><img alt="Backup 3" src="https://img.shields.io/badge/Backup%203-141e24.svg?&style=for-the-badge&logo=torproject&logoColor=white"></a></p>

# CipherChat
CipherChat is a console tool for secure and anonymous chatting with other people.

## 🚀 Installation
A. Use git
 1. Use the following command to download CipherChat
    ```bash
    git clone https://github.com/tn3w/CipherChat
    ```
 2. Go to the downloaded folder
    ```bash
    cd CipherChat
    ```
 3. Install all required packages
    ```bash
    python3 -m pip install -r requirements.txt
    ```
    Or create a virtual environment with python3-venv and install the packages
    ```bash
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    ```
 4. Launch CipherChat
    ```bash
    python3 main.py -h
    ```
    Or with a virtual environment:
    ```bash
    .venv/bin/python main.py -h
    ```

B. (Recommended for TOR users) Install via ZIP
 1. [Click here](https://github.com/tn3w/CipherChat/archive/refs/heads/master.zip) to download the ZIP file as a normal user or [here](http://tn3wtor4vgnrimugptubpaqsf2gc4pcsktknkxt74w7p5yzbt7rwrkid.onion/projects/CipherChat?as_zip=1) [Mirror 1](http://tn3wvjimrn3hydx4u52kzfnkgu6kffef2js27ewlhdf5htulno34vqad.onion/projects/CipherChat?as_zip=1) [Mirror 2](http://tn3wtor7cfz3epmuetrhkj3mangjxqpd47lxxicfwwdwja6dwq6dbdad.onion/projects/CipherChat?as_zip=1) as a Tor user
 2. Extract the downloaded ZIP packet with a packet manager or with the following command on Linux:
    ```bash
    unzip CipherChat-master.zip -d CipherChat
    ```
    Use the following if you downloaded it from the Tor Hidden Service:
    ```bash
    unzip CipherChat.zip -d CipherChat
    ```
 3. Go to the extracted folder
    ```bash
    cd CipherChat
    ```
 4. Install all required packages
    ```bash
    python3 -m pip install -r requirements.txt
    ```
    Or create a virtual environment with python3-venv and install the packages
    ```bash
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    ```
 5. Launch CipherChat
    ```bash
    python3 main.py -h
    ```
    Or with a virtual environment:
    ```bash
    .venv/bin/python3 main.py -h
    ```

## 🌉 Bridge types
### Vanilla Bridges
A Vanilla Tor Bridge is a basic type of bridge that helps users access the Tor network when regular access is blocked.
It disguises Tor traffic, making it harder for censors to identify and block it.

**Security:**
- Offers a basic level of protection by obfuscating Tor traffic.
- May be less effective in highly restrictive censorship environments where more sophisticated methods are employed to detect and block Tor traffic.

e.g.: `45.33.1.189:443 F9DFF618E7BA6C018245D417F39E970C2F019BAA`

### OBFS4 Bridges
OBFS4 (Obfuscation 4) is an improved version of the obfsproxy protocol, designed to better disguise Tor traffic.
It adds an extra layer of obfuscation to make it even more challenging for censors to recognize and block Tor usage.

**Security:**
- Provides a higher level of security compared to Vanilla bridges.
- Effective against more advanced censorship techniques, making it harder for authorities to identify and block Tor traffic.

e.g.: `obfs4 85.31.186.98:443 011F2599C0E9B27EE74B353155E244813763C3E5 cert=ayq0XzCwhpdysn5o0EyDUbmSOx3X/oTEbzDMvczHOdBJKlvIdHHLJGkZARtT4dcBFArPPg iat-mode=0`

### WebTunnel Bridges
WebTunnel is a type of bridge that disguises Tor traffic by making it look like regular web traffic.
It mimics the communication patterns of common web protocols, making it difficult for censors to distinguish Tor traffic from regular internet traffic.

**Security:**
- Offers a robust level of protection by blending Tor traffic with normal web traffic.
- Effective in circumventing censorship that focuses on blocking Tor specifically.

e.g.: `webtunnel [2001:db8:9443:367a:3276:1e74:91c3:7a5a]:443 54BF1146B161573185FBA0299B0DC3A8F7D08080 url=https://d3pyjtpvxs6z0u.cloudfront.net/Exei6xoh1aev8fiethee ver=0.0.1`

### Snowflake Bridges
Snowflake is unique as it relies on volunteers' web browsers to act as temporary proxies for users in censored regions.
When someone uses Tor with a Snowflake bridge, their traffic is routed through these volunteer-operated proxies, adding an extra layer of indirection.

**Security:**
- Provides a decentralized approach to bypassing censorship.
- While it helps against censorship, the security depends on the reliability of the volunteer-operated proxies.

e.g.: `snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 fingerprint=2B280B23E1107BB62ABFC40DDCC8824814F80A72 url=https://snowflake-broker.torproject.net.global.prod.fastly.net/ front=foursquare.com ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478,stun:stun.bluesip.net:3478,stun:stun.dus.net:3478,stun:stun.epygi.com:3478,stun:stun.sonetel.com:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.voys.nl:3478 utls-imitate=hellorandomizedalpn`

### Meek Lite (also known as Meek Azure) Bridges
Meek Lite uses cloud services, like Microsoft Azure, to disguise Tor traffic as innocuous-looking communication with these cloud services.
It makes Tor traffic appear similar to regular traffic to major cloud providers.

**Security:**
- Offers a high level of security by leveraging the reputation and ubiquity of major cloud services.
- Effective against censorship that targets Tor by making the traffic indistinguishable from common cloud service usage.

e.g.: `meek_lite 192.0.2.18:80 BE776A53492E1E044A26F17306E1BC46A55A1625 url=https://meek.azureedge.net/ front=ajax.aspnetcdn.com`

### Random Selection
Safely selects random bridges of all types

**Security:**
- Using a combination of bridge types provides a diverse and robust strategy to bypass censorship.
- However, the weaknesses of different bridge types come together and can have a negative impact on safety

### 👉🏼👤 Recommendation:
For users in highly censored regions, where the primary concern is overcoming censorship, OBFS4 is recommended for its robust obfuscation capabilities.
For users in regions with less censorship, Vanilla bridges may offer a good balance between performance and anonymity.

## 🛠️ Built-in or external bridges?
### Built-in
The client uses built-in bridges, which means that the bridges used for the obfuscated connection to the Tor service are already stored in the software and do not have to be queried externally.

**Benefits:**
- Offers simple configuration and faster use of CipherChat as bridges do not have to be queried or built-in bridges do not have to be selected first
- No dependency on external services such as BridgeDB

**Disadvantages:**
- Built-in bridges may already be blocked or detected by countries or organizations, which means that a certain entity knows that you are trying to use TOR or send or receive data anonymously

### External bridges
Bridges are queried from an external instance, either the official BridgeDB from Tor at [https://bridges.torproject.org/]() or an unofficial project on Github which collects bridges and has a larger collection of bridges: [https://github.com/scriptzteam/Tor-Bridges-Collector](https://github.com/scriptzteam/Tor-Bridges-Collector)
For a better distinction between the two options, there is a [section below](#-bridgedb-or-unofficial-project).

**Benefits:**
- External bridges offer better anti-censorship measures, as new bridges can be used.
- It gives the client greater flexibility, as different bridges can be selected.
- It is more resistant to blockages because, as mentioned above, new bridges are added every day and these can be utilized.

**Disadvantages:**
- There are delays because the client has to select the best bridge first
- When querying the bridges, built-in bridges are used first. Your traffic could be recognized here.

### 👉🏼👤 Recommendation:
Use built-in bridges if you don't want any effort, use external bridges if you want new / non-blocked bridges

## 💽 BridgeDB or unofficial project?
### BridgeDB
Tor's BridgeDB at [https://bridges.torproject.org/](https://bridges.torproject.org/) is the official interface that Tor Browser uses to request bridges

**Benefits:**
- The bridges provided are of high quality and do not need to be checked before use
- Using BridgeDB is safer

**Disadvantages:**
- BridgeDB always returns only 2 bridges per type, which does not offer high diversity
  e.g.:
  ```json
  [
    "193.182.000.000:37 SIGNATURE",
    "85.221.000.000:9001 SIGNATURE"
  ]
  ```
- BridgeDB requires a captcha before bridges can be downloaded

### Unofficial Github project
Bridges are downloaded from an automatic bridge collection project on Github: [https://github.com/scriptzteam/Tor-Bridges-Collector](https://github.com/scriptzteam/Tor-Bridges-Collector)

**Benefits:**
- Many bridges are being downloaded
- No captcha is required

**Disadvantages:**
- Some of the loaded bridges are already old, offline or slow, which means that bridges must first be validated, which can take time

### 👉🏼👤 Recommendation:
Use BridgeDB if you want good, secure bridges, don't use BridgeDB if you want diverse bridges 

## 🗃️ Use persistent storage?
Persistent storage refers to the storage of data over a longer period of time, even when the application is switched off. In the context of CipherChat, which is designed for privacy and anonymity, persistent storage refers to the fact that certain data, settings or files are stored on a disk and retained between sessions.
If you use Persisten Storage, your data is securely encrypted with a password and only then stored.

**Benefits:**
- Individual settings and configurations can be saved and do not have to be re-entered each time

**Disadvantages:**
- Persistent storage can be a security risk, if your password is compromised, private data such as your chat messages could be read

### 👉🏼👤 Recommendation:
You should ask yourself the following questions to check whether you should use Persistent Storage:
1. Is my Persistent Storage password secure?
2. Is facilitating the use of persistent storage, where, for example, passwords can be stored, not a concern for me in terms of compromising messages?

If you cannot clearly answer YES to both questions above, do not use persistent storage.

## 📖 What does CipherChat want to achieve?

CipherChat mainly tries to achieve the following:
- End-to-end encryption
- Easy to use even for normal users
- Anonymity of every user and server through the TOR network

The code should be easily understandable and verifiable so that the security can be checked and verified by several authorities, which also helps to find zero-day exploits more quickly.

## To do list
- [ ] ask for username and password
- [ ] save username and password encrypted
