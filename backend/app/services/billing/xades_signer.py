"""XAdES-BES digital signature for FacturaE 3.2.2."""
import base64
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import Certificate
from lxml import etree

DS = "http://www.w3.org/2000/09/xmldsig#"
XADES = "http://uri.etsi.org/01903/v1.3.2#"
C14N_ALG = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
RSA_SHA256 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
SHA256_ALG = "http://www.w3.org/2001/04/xmlenc#sha256"
ENVELOPED = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"


def _t(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _sha256b64(data: bytes) -> str:
    return _b64(hashlib.sha256(data).digest())


def _c14n(element: etree._Element) -> bytes:
    return etree.tostring(element, method="c14n", exclusive=False, with_comments=False)


def load_certificate_info(p12_path: str, password: str) -> dict:
    """Returns cert metadata without signing (for UI display)."""
    data = Path(p12_path).read_bytes()
    p12_obj = pkcs12.load_pkcs12(data, password.encode("utf-8") if password else b"")
    cert: Certificate = p12_obj.cert.certificate
    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial": str(cert.serial_number),
        "expires_at": cert.not_valid_after_utc.isoformat(),
    }


def sign_xml(xml_bytes: bytes, p12_path: str, password: str) -> bytes:
    """
    Signs FacturaE XML with XAdES-BES (enveloped, RSA-SHA256, C14N).
    Appends <ds:Signature> as last child of the root element.
    """
    data = Path(p12_path).read_bytes()
    p12_obj = pkcs12.load_pkcs12(data, password.encode("utf-8") if password else b"")
    private_key = p12_obj.key
    cert: Certificate = p12_obj.cert.certificate

    cert_der = cert.public_bytes(serialization.Encoding.DER)
    cert_b64 = _b64(cert_der)
    cert_digest = _sha256b64(cert_der)
    issuer_name = cert.issuer.rfc4514_string()
    serial_number = str(cert.serial_number)
    signing_time = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    sig_id = "Signature-Invoice"
    signed_props_id = "SignedProperties"

    # 1. Parse document and compute its digest (Signature not yet appended)
    root = etree.fromstring(xml_bytes)
    doc_c14n = _c14n(root)
    doc_digest = _sha256b64(doc_c14n)

    # 2. Build SignedProperties and compute its digest
    qualifying = etree.Element(
        _t(XADES, "QualifyingProperties"),
        nsmap={"xades": XADES, "ds": DS},
        attrib={"Target": f"#{sig_id}"},
    )
    signed_props = etree.SubElement(
        qualifying, _t(XADES, "SignedProperties"), attrib={"Id": signed_props_id}
    )
    ssp = etree.SubElement(signed_props, _t(XADES, "SignedSignatureProperties"))
    etree.SubElement(ssp, _t(XADES, "SigningTime")).text = signing_time

    signing_cert_el = etree.SubElement(ssp, _t(XADES, "SigningCertificate"))
    cert_el = etree.SubElement(signing_cert_el, _t(XADES, "Cert"))
    cert_digest_el = etree.SubElement(cert_el, _t(XADES, "CertDigest"))
    etree.SubElement(cert_digest_el, _t(DS, "DigestMethod"), attrib={"Algorithm": SHA256_ALG})
    etree.SubElement(cert_digest_el, _t(DS, "DigestValue")).text = cert_digest
    issuer_serial = etree.SubElement(cert_el, _t(XADES, "IssuerSerial"))
    etree.SubElement(issuer_serial, _t(DS, "X509IssuerName")).text = issuer_name
    etree.SubElement(issuer_serial, _t(DS, "X509SerialNumber")).text = serial_number

    signed_props_c14n = _c14n(signed_props)
    signed_props_digest = _sha256b64(signed_props_c14n)

    # 3. Build SignedInfo with both References
    signed_info = etree.Element(_t(DS, "SignedInfo"), nsmap={"ds": DS})
    etree.SubElement(signed_info, _t(DS, "CanonicalizationMethod"), attrib={"Algorithm": C14N_ALG})
    etree.SubElement(signed_info, _t(DS, "SignatureMethod"), attrib={"Algorithm": RSA_SHA256})

    ref_doc = etree.SubElement(
        signed_info, _t(DS, "Reference"), attrib={"Id": "Reference-Invoice", "URI": ""}
    )
    transforms = etree.SubElement(ref_doc, _t(DS, "Transforms"))
    etree.SubElement(transforms, _t(DS, "Transform"), attrib={"Algorithm": ENVELOPED})
    etree.SubElement(ref_doc, _t(DS, "DigestMethod"), attrib={"Algorithm": SHA256_ALG})
    etree.SubElement(ref_doc, _t(DS, "DigestValue")).text = doc_digest

    ref_props = etree.SubElement(
        signed_info, _t(DS, "Reference"),
        attrib={
            "Id": "Reference-SignedProperties",
            "URI": f"#{signed_props_id}",
            "Type": "http://uri.etsi.org/01903#SignedProperties",
        },
    )
    etree.SubElement(ref_props, _t(DS, "DigestMethod"), attrib={"Algorithm": SHA256_ALG})
    etree.SubElement(ref_props, _t(DS, "DigestValue")).text = signed_props_digest

    # 4. Canonicalize SignedInfo and sign
    signed_info_c14n = _c14n(signed_info)
    sig_value = private_key.sign(signed_info_c14n, asym_padding.PKCS1v15(), hashes.SHA256())

    # 5. Assemble Signature element
    signature = etree.Element(
        _t(DS, "Signature"),
        nsmap={"ds": DS, "xades": XADES},
        attrib={"Id": sig_id},
    )
    signature.append(signed_info)
    etree.SubElement(signature, _t(DS, "SignatureValue")).text = _b64(sig_value)

    key_info = etree.SubElement(signature, _t(DS, "KeyInfo"))
    x509_data = etree.SubElement(key_info, _t(DS, "X509Data"))
    etree.SubElement(x509_data, _t(DS, "X509Certificate")).text = cert_b64

    obj = etree.SubElement(signature, _t(DS, "Object"), attrib={"Id": "QualifyingPropertiesObject"})
    obj.append(qualifying)

    root.append(signature)

    xml_str = etree.tostring(root, encoding="unicode", xml_declaration=False)
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str.encode("utf-8")
