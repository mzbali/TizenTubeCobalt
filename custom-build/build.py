#!/usr/bin/env python3
"""Compile our Android sources and bundle them with the unmodified upstream engine.

Requires JDK 21, Android platform 35, build-tools 35.0.0, and Apktool 2.12.1.
The tools are external inputs, not committed binaries. Signing keys stay local.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
TOOLS = Path(os.environ.get('TV_TOOLS', PROJECT / '.tools'))
JAVA_HOME = Path(os.environ.get('JAVA_HOME', TOOLS / 'jdk-21.0.12.1+1/Contents/Home'))
JAVA = JAVA_HOME / 'bin/java'
SDK = Path(os.environ.get('TV_BUILD_TOOLS', TOOLS / 'android-15'))
ANDROID_JAR = Path(os.environ.get('TV_ANDROID_JAR', TOOLS / 'android-35/android.jar'))
APKTOOL = Path(os.environ.get('TV_APKTOOL', TOOLS / 'apktool.jar'))
BASE = ROOT / 'inputs/cobalt-arm-v2.0.3.apk'
BASE_SHA = '72a3527f520db3a1b414916ad96481244e451c41e272ae33344ae5e79abb37dd'
SCRIPT = PROJECT / 'scripts/mods/features/instantSpeed.js'
OUT = ROOT / 'out'
DECODED = OUT / 'decoded'
ENV = dict(os.environ, JAVA_HOME=str(JAVA_HOME))
PACKAGE = 'io.github.mzbali.tizentube'
NS = 'http://schemas.android.com/apk/res/android'
A = '{' + NS + '}'

def run(*args):
    subprocess.run([str(a) for a in args], check=True, env=ENV)

def main():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA:
        raise SystemExit('Upstream APK hash mismatch; review the new release before rebuilding.')
    OUT.mkdir(exist_ok=True)
    # Decode anew on each build. Inputs and signing material are outside this directory.
    run(JAVA, '-jar', APKTOOL, 'd', '-f', '-s', BASE, '-o', DECODED)
    manifest = ET.parse(DECODED / 'AndroidManifest.xml')
    root = manifest.getroot()
    old_package = root.get('package')
    root.set('package', PACKAGE)
    root.set(A + 'versionName', '2.0.3-speed.2')
    root.set(A + 'versionCode', '20302')
    app = root.find('application')
    app.set(A + 'label', 'YouTube')
    app.set(A + 'debuggable', 'false')
    for element in app.iter():
        for attribute, value in list(element.attrib.items()):
            if old_package in value:
                element.set(attribute, value.replace(old_package, PACKAGE))
    for activity in app.findall('activity'):
        if activity.get(A + 'name') == 'dev.cobalt.app.MainActivity':
            activity.set(A + 'name', PACKAGE + '.SpeedActivity')
    receiver = ET.SubElement(app, 'receiver', {
        A + 'name': PACKAGE + '.SpeedReceiver', A + 'exported': 'true'
    })
    # Explicit component broadcasts are used by Key Mapper; no arbitrary JS extras.
    manifest.write(DECODED / 'AndroidManifest.xml', encoding='utf-8', xml_declaration=True)
    config = DECODED / 'apktool.yml'
    text = config.read_text().replace('versionCode: 203\n', 'versionCode: 20302\n')
    text = text.replace('versionName: 2.0.3\n', 'versionName: 2.0.3-speed.2\n')
    config.write_text(text)
    shutil.copy2(SCRIPT, DECODED / 'assets/instantSpeed.js')
    artwork = ROOT / 'artwork/Youtube.png'
    for pattern in ['mipmap*/ic_app', 'drawable*/app_banner']:
        for target in (DECODED / 'res').glob(pattern):
            shutil.copy2(artwork, target)

    # A compile-only declaration of the upstream superclass. This is NEVER packaged.
    stubs = OUT / 'stubs'
    stub = stubs / 'dev/cobalt/app/MainActivity.java'
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text('package dev.cobalt.app; public class MainActivity extends '
                    'android.app.Activity { public void evaluateJavaScript(String js) {} }')
    stub_classes = OUT / 'stub-classes'
    classes = OUT / 'classes'
    dex = OUT / 'dex'
    for directory in [stub_classes, classes, dex]:
        directory.mkdir(exist_ok=True)
    run(JAVA_HOME / 'bin/javac', '-source', '8', '-target', '8', '-classpath',
        ANDROID_JAR, '-d', stub_classes, stub)
    run(JAVA_HOME / 'bin/javac', '-source', '8', '-target', '8', '-classpath',
        str(ANDROID_JAR) + os.pathsep + str(stub_classes), '-d', classes,
        *sorted((ROOT / 'src').rglob('*.java')))
    run(JAVA, '-cp', SDK / 'lib/d8.jar', 'com.android.tools.r8.D8', '--min-api', '24',
        '--lib', ANDROID_JAR, '--classpath', stub_classes, '--output', dex,
        *sorted(classes.rglob('*.class')))
    shutil.copy2(dex / 'classes.dex', DECODED / 'classes4.dex')
    unsigned = OUT / 'youtube-speed-unsigned.apk'
    run(JAVA, '-jar', APKTOOL, 'b', DECODED, '-o', unsigned)
    aligned = OUT / 'youtube-speed-aligned.apk'
    run(SDK / 'zipalign', '-f', '-P', '16', '4', unsigned, aligned)
    keys = ROOT / 'keys'
    keys.mkdir(exist_ok=True, mode=0o700)
    keystore = keys / 'youtube-speed.jks'
    password_file = keys / 'password'
    if not keystore.exists():
        import secrets
        password_file.write_text(secrets.token_urlsafe(32))
        password_file.chmod(0o600)
        run(JAVA_HOME / 'bin/keytool', '-genkeypair', '-keystore', keystore,
            '-storepass:file', password_file, '-keypass:file', password_file,
            '-alias', 'youtube-speed', '-keyalg', 'RSA', '-keysize', '3072',
            '-validity', '10000', '-dname', 'CN=YouTube Speed Local Build')
        keystore.chmod(0o600)
    final = OUT / 'youtube-speed.apk'
    run(JAVA, '-jar', SDK / 'lib/apksigner.jar', 'sign', '--ks', keystore,
        '--ks-pass', 'file:' + str(password_file), '--ks-key-alias', 'youtube-speed',
        '--out', final, aligned)
    print('Built', final)
    print('SHA256', hashlib.sha256(final.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
