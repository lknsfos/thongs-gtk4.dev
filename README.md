# 👙 ThongSSH

**Minimalist. Sexy. Secure?**

Welcome to **ThongSSH** — the lightest and hottest SSH/Telnet/SFTP client for Linux.

Just like the perfect pair of thongs, this client is barely there, but it holds everything together (your connections!) perfectly. No bulky "granny panty" interface here, just pure functionality and pleasure.

## ✨ About the Look

ThongSSH is for those who love minimalism. We’ve got a cute host panel so you never lose track of your servers.

### 🛠️ The Fabric (Tech Stack)
Stitched together with the latest fashion trends:
* **Python 3.10+** (Fresh and hot 🔥)
* **GTK 4 & Libadwaita 1** (Smooth and sleek interface)
* **Paramiko** (For that extra spicy SFTP)

## ⚠️ WARNING: Experimental Zone

Listen, let's be real:

1.  **AI Collaboration:** This whole thing started as an AI fantasy, but now it's our little secret project. A human (hi!) and AI (that's me, xoxo) worked on this together.
2.  **Pre-Alpha / Experimental:** It’s not even beta, it’s a "fitting session". It might feel tight, it might slip, or it might crash when you least expect it. Use at your own risk!
3.  **Security:** We tried, but the code audit was done by electric sheep. So... you get the picture.

## 💅 What You'll Need (Installation)

To get this party started, you'll need a few things.

### For Ubuntu / Debian Babes:
```bash
# Install system libraries for GTK4, terminal, and the actual clients
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-vte-1 openssh-client telnet
```

### For Fedora / RHEL Cuties:
```bash
# The packages have slightly different names here, but it's the same vibe
sudo dnf install python3-gobject gtk4 libadwaita vte-ng openssh-clients telnet
```

### And for everyone, via pip:
> Don't forget `pip`! It's for the spiciest part — SFTP.
```bash
pip install paramiko
```

##  Packages & Updates

When will we get `.deb` or `.rpm`?
> *Ugh, don't pressure me!* 💅

Updates and packages will happen **someday**. Maybe. If the vibe is right. For now — clone it, run from source, and enjoy the thrill.

## 🚀 How to Run (For the brave)

Make sure you've installed everything, then run:

```bash
git clone git@github.com:lknsfos/thongs-gtk4.dev.git
cd thongs-gtk4.dev
# Install dependencies if you haven't already
# pip install paramiko
python3 thongssh.py
```

_Made with 💖, Python & AI hallucinations._