# Turn off screensaver
gconftool-2 --set -t boolean /apps/gnome-screensaver/idle_activation_enabled false

# Use browser window instead of Nautilus
gconftool-2 --set -t boolean /apps/nautilus/preferences/always_use_browser true

# Disable the disk check utility on autostart
mkdir -p "${HOME}/.config/autostart"
cat "/etc/xdg/autostart/gdu-notification-daemon.desktop" <(echo "X-GNOME-Autostart-enabled=false") > "${HOME}/.config/autostart/gdu-notification-daemon.desktop"

# Remove any preconfigured monitors
if [[ -f "${HOME}/.config/monitors.xml" ]]; then
  mv "${HOME}/.config/monitors.xml" "${HOME}/.config/monitors.xml.bak"
fi

# Ensure DBus uses system paths
export TMPDIR=/tmp
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Start DBus with the correct configuration
eval $(env TMPDIR=/tmp XDG_RUNTIME_DIR=/run/user/$(id -u) /usr/bin/dbus-launch --sh-syntax)

# Start up Gnome desktop (block until user logs out)
exec /etc/X11/xinit/Xsession gnome-session

