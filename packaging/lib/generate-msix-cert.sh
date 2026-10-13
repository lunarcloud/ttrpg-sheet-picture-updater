#!/usr/bin/env bash
# Generates an ephemeral self-signed PFX certificate for signing the MSIX,
# used only when the caller hasn't supplied a real code-signing certificate
# via MSIX_PFX_FILE. Never committed — regenerated per build.
#
# MSIX packages generally must be signed to install at all, even with a
# self-signed certificate — Windows will refuse to install an unsigned
# one. Since this project has no paid code-signing certificate, this is
# the accepted trade-off (see packaging/README.md's MSIX section): the
# package is signed, but end users must manually import/trust the
# generated certificate's public half before Windows will allow
# installation. There's no way around that without a real certificate.
#
# Uses PowerShell's New-SelfSignedCertificate/Export-PfxCertificate
# (built into every windows-latest runner) rather than requiring openssl,
# since build-msix.sh otherwise has no non-Windows-native dependencies.
set -euo pipefail

# generate_self_signed_msix_cert <subject> <out_pfx_path> <passphrase>
generate_self_signed_msix_cert() {
    local subject="$1"
    local out_pfx="$2"
    local passphrase="$3"

    local win_out_pfx
    win_out_pfx="$(cygpath -w "$out_pfx")"

    powershell.exe -NoProfile -Command "
        \$ErrorActionPreference = 'Stop'
        \$cert = New-SelfSignedCertificate \`
            -Type Custom \`
            -Subject '$subject' \`
            -KeyUsage DigitalSignature \`
            -FriendlyName 'set-ttrpg-portrait MSIX signing (ephemeral, build-time only)' \`
            -CertStoreLocation 'Cert:\\CurrentUser\\My' \`
            -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3', '2.5.29.19={text}Subject Type:End Entity')
        \$pwd = ConvertTo-SecureString -String '$passphrase' -Force -AsPlainText
        \$exportParams = @{ Cert = \$cert; FilePath = '$win_out_pfx'; Password = \$pwd }
        Export-PfxCertificate @exportParams | Out-Null
        Remove-Item \"Cert:\\CurrentUser\\My\\\$(\$cert.Thumbprint)\"
    "
}

# export_msix_public_cert <pfx_path> <passphrase> <out_cer_path>
#
# Exports just the public certificate (no private key) from a PFX, so it
# can be shipped alongside the .msix for end users to trust before
# installing — see build-msix.sh's usage.
export_msix_public_cert() {
    local pfx_path="$1"
    local passphrase="$2"
    local out_cer="$3"

    local win_pfx_path win_out_cer
    win_pfx_path="$(cygpath -w "$pfx_path")"
    win_out_cer="$(cygpath -w "$out_cer")"

    powershell.exe -NoProfile -Command "
        \$ErrorActionPreference = 'Stop'
        \$cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new('$win_pfx_path', '$passphrase')
        [System.IO.File]::WriteAllBytes('$win_out_cer', \$cert.Export('Cert'))
        \$cert.Dispose()
    "
}
