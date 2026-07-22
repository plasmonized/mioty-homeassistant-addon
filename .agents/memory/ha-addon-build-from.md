---
name: HA add-on BUILD_FROM deprecation
description: Why the add-on Dockerfile must not rely on Supervisor passing BUILD_FROM
---
Rule: Never use `ARG BUILD_FROM` / `FROM $BUILD_FROM` in the HA add-on Dockerfile. Supervisor 2026.04+ no longer passes BUILD_FROM (build.yaml and config.yaml build_from are ignored) — build fails with "base name ($BUILD_FROM) should not be blank".

**Why:** HA deprecated the legacy builder; base images should be referenced directly in the Dockerfile. The multi-arch `ghcr.io/home-assistant/base` manifest only exists from tag 3.21 and covers amd64+arm64 only; per-arch images (`{arch}-base:3.19`) still exist for armhf/armv7/i386.

**How to apply:** Use `ARG BUILD_ARCH=amd64` before `FROM ghcr.io/home-assistant/${BUILD_ARCH}-base:<tag>` (default prevents blank base). Supervisor still passes BUILD_ARCH. Also: user installs from github.com/plasmonized/mioty-homeassistant-addon — changes only take effect after pushing there, and HA needs a version bump to rebuild.
