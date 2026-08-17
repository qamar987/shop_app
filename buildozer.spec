[app]

title = Cloth Shop Manager
package.name = clothshop
package.domain = org.nasir

source.dir = .
source.include_exts = py,db,png,jpg,jpeg

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

[app:android]

android.api = 35
android.minapi = 24
android.archs = arm64-v8a

android.permissions =

[buildozer]

log_level = 2
warn_on_root = 1
