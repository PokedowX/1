[app]
title = Habit Builder
package.name = habitbuilder
package.domain = org.kritish
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
icon.filename = icon.png
presplash.filename = presplash.png
orientation = portrait
fullscreen = 1
entrypoint = main.py

# Required dependencies
requirements = python3,kivy

# Permissions
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET

# Android build settings
android.minapi = 21
android.api = 31
android.ndk = 23b
android.arch = armeabi-v7a
android.enable_androidx = 1

[buildozer]
log_level = 2
warn_on_root = 1

