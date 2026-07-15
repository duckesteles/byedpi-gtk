<div align="center">

# byedpi-gtk

A GTK4/libadwaita frontend for [byedpi](https://github.com/hufrea/byedpi) that
bypasses deep packet inspection through a local SOCKS5 proxy. Privacy-focused,
no telemetry, built for every Linux distribution.

</div>

> [!CAUTION]
> byedpi-gtk is provided for **educational and research purposes only**. It is a
> graphical frontend for the independent
> [byedpi](https://github.com/hufrea/byedpi) project and does not host, provide,
> promote, or grant access to any specific website, service, or content.
>
> You are **solely responsible** for how you use this software and for ensuring
> that your use complies with all laws, regulations, and terms of service that
> apply in your country and jurisdiction. It is your responsibility to know and
> follow the ones that apply to you.
>
> This software is provided "as is", **without any warranty of any kind**. To the
> fullest extent permitted by law, the author and contributors accept **no
> responsibility and no liability** for any use or misuse of this software, or for
> any direct or indirect damage, loss, or legal consequence arising from it. By
> downloading, installing, or using byedpi-gtk you agree that you do so entirely
> at your own risk and that you assume full responsibility for your actions. If
> you do not agree with these terms, do not download, install, or use it.

## Features

- One-click connect and disconnect to a local byedpi (ciadpi) SOCKS5 proxy.
- Keeps the byedpi core up to date automatically at startup.
- Editable byedpi arguments, defaulting to `--tlsrec 1+s`.
- Follows the system light/dark theme, with a manual override.
- Settings save instantly, no save button.
- Localized, with the language following your system and selectable in settings.

## Install

### Flatpak

Download `byedpi-gtk.flatpak` from the
[latest release](https://github.com/duckesteles/byedpi-gtk/releases/latest):

```sh
flatpak install --user ./byedpi-gtk.flatpak
flatpak run io.github.duckesteles.byedpigtk
```

### Arch Linux (AUR)

```sh
paru -S byedpi-gtk
```

### AppImage

Pick the build for your CPU (`x86_64` or `aarch64`):

```sh
chmod +x byedpi-gtk-x86_64.AppImage
./byedpi-gtk-x86_64.AppImage
```

### Debian / Ubuntu

A single package covers every architecture:

```sh
sudo apt install ./byedpi-gtk_*_all.deb
```

## Usage

Launch byedpi-gtk, wait for the startup update check, then press **Connect**.
Point your applications at the SOCKS5 endpoint shown in the window
(`127.0.0.1:1080` by default). Adjust the port and byedpi arguments under
**Settings**.

## Build from source

Requires `meson`, `ninja`, `gtk4`, `libadwaita`, `python-gobject` and `gettext`.

```sh
meson setup build --prefix=/usr
meson compile -C build
sudo meson install -C build
```

byedpi-gtk looks for the `ciadpi` binary in its data directory, then any bundled
copy, then your `PATH`. When update checks are enabled it downloads the matching
`ciadpi` build from the byedpi project on first run.

## Translating

Add your language code to `po/LINGUAS`, create `po/<code>.po` from
`po/byedpi-gtk.pot`, translate it, and rebuild. The source language is English
and is used as the fallback.

## License

byedpi-gtk is released under the [GPL-3.0-or-later](LICENSE). It bundles the
[byedpi](https://github.com/hufrea/byedpi) core, which is distributed under the
MIT license.
