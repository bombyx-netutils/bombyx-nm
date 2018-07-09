PACKAGE_VERSION=0.0.1
prefix=/usr

clean:

install:
	install -d -m 0755 "$(DESTDIR)/$(prefix)/bin"
	install -m 0755 bombyx "$(DESTDIR)/$(prefix)/bin"

	install -d -m 0755 "$(DESTDIR)/$(prefix)/sbin"
	install -m 0755 bombyx-daemon "$(DESTDIR)/$(prefix)/sbin"

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib/bombyx"
	cp -r lib/* "$(DESTDIR)/$(prefix)/lib/bombyx"
	find "$(DESTDIR)/$(prefix)/lib/bombyx" -type f | xargs chmod 644
	find "$(DESTDIR)/$(prefix)/lib/bombyx" -type d | xargs chmod 755

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib/systemd/system"
	install -m 0644 data/bombyx-daemon.service "$(DESTDIR)/$(prefix)/lib/systemd/system"

	install -d -m 0755 "$(DESTDIR)/etc/dbus-1/system.d"
	install -m 0644 data/org.fpemud.Bombyx.conf "$(DESTDIR)/etc/dbus-1/system.d"
	install -m 0644 data/org.fpemud.IpForward.conf "$(DESTDIR)/etc/dbus-1/system.d"

uninstall:
	rm -Rf "$(DESTDIR)/$(prefix)/bin/bombyx"
	rm -Rf "$(DESTDIR)/$(prefix)/sbin/bombyx-daemon"
	rm -Rf "$(DESTDIR)/$(prefix)/lib/bombyx"
	rm -f "$(DESTDIR)/$(prefix)/lib/systemd/system/bombyx-daemon.service"
	rm -f "$(DESTDIR)/$(prefix)/etc/dbus-1/system.d/org.fpemud.Bombyx.conf"
	rm -f "$(DESTDIR)/$(prefix)/etc/dbus-1/system.d/org.fpemud.IpForward.conf"

.PHONY: all clean install uninstall
