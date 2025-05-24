# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import socket

import xbmc
import xbmcaddon


__scriptid__ = 'service.libreelec.settings'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
__cwd__ = __addon__.getAddonInfo('path')
__media__ = f'{__cwd__}/resources/skins/Default/media'
_ = __addon__.getLocalizedString

sock = None
try:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0) # 5 seconds timeout
    sock.connect('/var/run/service.libreelec.settings.sock')
    sock.sendall(bytes('openConfigurationWindow', 'utf-8')) # Use sendall
except socket.timeout:
    xbmc.log(f"LibreELEC: Timeout connecting to service at {__scriptid__}", level=xbmc.LOGERROR)
    # Assuming _(32390) is "Cannot connect to service" or similar, which is still relevant for timeout.
    # If a specific "Timeout connecting to service" string like _(32391) exists, it could be used.
    xbmc.executebuiltin(f'Notification("LibreELEC", "{_(32390)}", 5000, "{__media__}/icon.png"')
except socket.error as e:
    xbmc.log(f"LibreELEC: Error connecting to service at {__scriptid__}: {e}", level=xbmc.LOGERROR)
    xbmc.executebuiltin(f'Notification("LibreELEC", "{_(32390)}", 5000, "{__media__}/icon.png"')
except Exception as e:
    xbmc.log(f"LibreELEC: Unknown error connecting to service at {__scriptid__}: {e}", level=xbmc.LOGERROR)
    xbmc.executebuiltin(f'Notification("LibreELEC", "{_(32390)}", 5000, "{__media__}/icon.png"')
finally:
    if sock:
        sock.close()
