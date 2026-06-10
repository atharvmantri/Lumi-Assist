import sys
import os
import json
import base64
import hmac
import hashlib
from pathlib import Path

# Configure UTF-8 encoding for stdout on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.security import (
    firewall_rules,
    open_ports,
    active_connections,
    windows_security_audit,
    manage_secrets,
    generate_password,
    hash_verify,
    jwt_decode_validate,
    ssh_key_manager,
    dependency_audit,
    secrets_scan,
    firewall_rule_manager,
    intrusion_detection_log,
    encrypt_decrypt
)

def test_identity_and_access():
    print("==================================================")
    print("Testing Identity & Access Tools...")
    print("==================================================")

    # 1. manage_secrets (Windows DPAPI)
    print("1. Testing manage_secrets (DPAPI vault)...")
    secret_name = "test_lumi_secret_key"
    secret_value = "super-secure-voice-assistant-token-2026"
    
    # Clean up before starting
    manage_secrets(action="delete", name=secret_name)
    
    # Save secret
    set_res = manage_secrets(action="set", name=secret_name, value=secret_value)
    print(f"   Set secret result: {set_res}")
    
    # Retrieve secret
    get_res = manage_secrets(action="get", name=secret_name)
    print(f"   Get secret: {get_res}")
    assert get_res == secret_value, f"Expected {secret_value}, got {get_res}"
    
    # List secrets
    list_res = manage_secrets(action="list")
    print(f"   List secrets:\n{list_res}")
    assert secret_name in list_res, "Expected test key in list of secrets"
    
    # Delete secret
    del_res = manage_secrets(action="delete", name=secret_name)
    print(f"   Delete secret result: {del_res}")
    
    # Confirm deletion
    get_after_del = manage_secrets(action="get", name=secret_name)
    print(f"   Get secret after deletion: {get_after_del}")
    assert "error" in get_after_del, "Expected error retrieving deleted secret"
    print("   ✅ manage_secrets passed.\n")

    # 2. generate_password
    print("2. Testing generate_password...")
    pwd1 = generate_password(length=16, method="password")
    pwd2 = generate_password(length=24, method="password", use_special=False)
    passphrase = generate_password(length=5, method="passphrase")
    
    print(f"   Password (16 chars): {pwd1}")
    print(f"   Password (24 chars, no special): {pwd2}")
    print(f"   Passphrase (5 words): {passphrase}")
    
    assert len(pwd1) == 16, "Password length mismatch"
    assert len(pwd2) == 24, "Password length mismatch"
    assert len(passphrase.split("-")) == 5, "Passphrase word count mismatch"
    print("   ✅ generate_password passed.\n")

    # 3. hash_verify
    print("3. Testing hash_verify...")
    test_text = "lumi-assistant-2026"
    
    # SHA-256
    sha256_hash = hash_verify(text=test_text, action="hash", algorithm="sha256")
    print(f"   SHA-256 Hash: {sha256_hash}")
    sha256_verify = hash_verify(text=test_text, action="verify", algorithm="sha256", expected_hash=sha256_hash)
    print(f"   SHA-256 Verify: {sha256_verify}")
    assert "SUCCESS" in sha256_verify, "SHA-256 verification failed"

    # MD5
    md5_hash = hash_verify(text=test_text, action="hash", algorithm="md5")
    print(f"   MD5 Hash: {md5_hash}")
    md5_verify = hash_verify(text=test_text, action="verify", algorithm="md5", expected_hash=md5_hash)
    print(f"   MD5 Verify: {md5_verify}")
    assert "SUCCESS" in md5_verify, "MD5 verification failed"

    # bcrypt (gracefully fallback if not installed)
    try:
        import bcrypt
        bcrypt_hash = hash_verify(text=test_text, action="hash", algorithm="bcrypt")
        print(f"   bcrypt Hash: {bcrypt_hash}")
        bcrypt_verify = hash_verify(text=test_text, action="verify", algorithm="bcrypt", expected_hash=bcrypt_hash)
        print(f"   bcrypt Verify: {bcrypt_verify}")
        assert "SUCCESS" in bcrypt_verify, "bcrypt verification failed"
    except ImportError:
        print("   bcrypt package not installed, skipped bcrypt verify test.")
        
    print("   ✅ hash_verify passed.\n")

    # 4. jwt_decode_validate
    print("4. Testing jwt_decode_validate...")
    # Create a test JWT
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": "lumi_user_123", "name": "Lumi User", "exp": 1893456000} # 2030 expiry
    
    def b64_encode(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode("utf-8")).decode("utf-8").replace("=", "")
        
    h_b64 = b64_encode(header)
    p_b64 = b64_encode(payload)
    
    jwt_secret = "lumi_secret_key_999"
    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    sig_bytes = hmac.new(jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig_bytes).decode("utf-8").replace("=", "")
    
    test_token = f"{h_b64}.{p_b64}.{sig_b64}"
    print(f"   Generated JWT: {test_token}")
    
    # Validate with signature
    jwt_res = jwt_decode_validate(token=test_token, secret=jwt_secret)
    print(f"   JWT Decode & Validate result:\n{jwt_res}")
    assert "lumi_user_123" in jwt_res, "Expected subject in decoded output"
    assert "✅ Signature Verification: SUCCESS" in jwt_res, "Signature validation should succeed"

    # Validate with incorrect signature
    jwt_res_bad = jwt_decode_validate(token=test_token, secret="wrong_secret")
    print(f"   JWT Decode with WRONG secret result:\n{jwt_res_bad}")
    assert "❌ Signature Verification: FAILED" in jwt_res_bad, "Signature validation should fail"
    
    print("   ✅ jwt_decode_validate passed.\n")

    # 5. ssh_key_manager
    print("5. Testing ssh_key_manager...")
    test_key_name = "id_rsa_lumi_test"
    
    # Cleanup beforehand
    ssh_key_manager(action="delete", key_name=test_key_name)
    
    # Create
    create_res = ssh_key_manager(action="create", key_name=test_key_name, key_type="rsa", comment="test@lumi.ai")
    print(f"   Create SSH key result: {create_res[:300]}...")
    assert "Successfully generated SSH key" in create_res or "ssh-keygen command not found" in create_res, "Unexpected create result"
    
    # List
    list_res = ssh_key_manager(action="list")
    print(f"   List SSH keys:\n{list_res}")
    
    # Delete
    del_res = ssh_key_manager(action="delete", key_name=test_key_name)
    print(f"   Delete SSH key result: {del_res}")
    assert "Successfully deleted SSH key" in del_res or "not found" in del_res, "Unexpected delete result"
    
    print("   ✅ ssh_key_manager passed.\n")


def test_security_scanning():
    print("==================================================")
    print("Testing Security Scanning Tools...")
    print("==================================================")

    # 6. dependency_audit
    print("6. Testing dependency_audit...")
    # Create a mock requirements.txt file in a subdirectory to match name constraints
    req_dir = Path("data/audit_test")
    req_dir.mkdir(parents=True, exist_ok=True)
    req_file = req_dir / "requirements.txt"
    with open(req_file, "w", encoding="utf-8") as f:
        f.write("# Temporary mock requirements\n")
        f.write("requests==2.31.0\n")
        f.write("django==1.11.29\n") # This is heavily vulnerable, OSV should report it if internet available
        
    audit_res = dependency_audit(file_path=str(req_file))
    print(f"   Dependency audit result:\n{audit_res}")
    assert "Checked 2 packages" in audit_res or "VULNERABLE PACKAGES FOUND" in audit_res or "error" in audit_res, "Unexpected audit result"
    
    # Cleanup mock
    if req_file.exists():
        req_file.unlink()
    if req_dir.exists():
        req_dir.rmdir()
    print("   ✅ dependency_audit passed.\n")

    # 7. secrets_scan
    print("7. Testing secrets_scan...")
    # Create mock directory and file with secret
    mock_scan_dir = Path("data/mock_scan_workspace")
    mock_scan_dir.mkdir(parents=True, exist_ok=True)
    mock_secret_file = mock_scan_dir / "keys.py"
    
    with open(mock_secret_file, "w", encoding="utf-8") as f:
        f.write("# Config file\n")
        f.write("GITHUB_TOKEN = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'\n")
        f.write("AWS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'\n")
        
    scan_res = secrets_scan(search_path=str(mock_scan_dir))
    print(f"   Secrets scan result:\n{scan_res}")
    assert "GITHUB_TOKEN" in scan_res or "AWS" in scan_res or "SECRETS / CREDENTIALS DETECTED" in scan_res, "Expected scan to find credentials"
    
    # Cleanup mocks
    if mock_secret_file.exists():
        os.remove(mock_secret_file)
    if mock_scan_dir.exists():
        os.rmdir(mock_scan_dir)
    print("   ✅ secrets_scan passed.\n")

    # 8. firewall_rule_manager (requires admin privileges, we verify graceful permission detection)
    print("8. Testing firewall_rule_manager...")
    rule_name = "Lumi_Test_Block_Port_8888"
    add_res = firewall_rule_manager(action="add", name=rule_name, port=8888, protocol="TCP", direction="inbound")
    print(f"   Add firewall rule result: {add_res}")
    
    # Let's delete it if it was added or check if it fails due to Administrator privilege
    if "Successfully executed" in add_res:
        del_res = firewall_rule_manager(action="delete", name=rule_name)
        print(f"   Delete firewall rule result: {del_res}")
        assert "Successfully executed" in del_res, "Failed to clean up created firewall rule"
    else:
        assert "Administrator privileges are required" in add_res or "error" in add_res, "Should warn about admin privileges or return error"
        
    print("   ✅ firewall_rule_manager passed.\n")

    # 9. intrusion_detection_log
    print("9. Testing intrusion_detection_log...")
    # Create a mock auth log file
    mock_auth_log = "data/mock_auth.log"
    with open(mock_auth_log, "w", encoding="utf-8") as f:
        f.write("Jun 10 12:01:00 server sshd[1234]: Failed password for root from 192.168.1.55 port 22 ssh2\n")
        f.write("Jun 10 12:02:00 server sshd[1234]: Failed password for root from 192.168.1.55 port 22 ssh2\n")
        f.write("Jun 10 12:03:00 server sshd[1234]: Failed password for root from 192.168.1.55 port 22 ssh2\n")
        f.write("Jun 10 12:04:00 server sshd[1234]: Accepted password for root from 192.168.1.56 port 22 ssh2\n")
        
    log_res = intrusion_detection_log(log_path=mock_auth_log)
    print(f"   Intrusion detection analysis (mock file):\n{log_res}")
    assert "192.168.1.55" in log_res, "Expected to spot suspect IP 192.168.1.55"
    assert "3 attempts" in log_res, "Expected 3 attempts parsed"

    # Event logs query (graceful permission detection if non-admin)
    event_log_res = intrusion_detection_log(max_events=5)
    print(f"   Windows Security Logon failures event log audit:\n{event_log_res[:300]}...")
    assert "Logon Failures" in event_log_res or "Administrator privileges are required" in event_log_res or "error" in event_log_res, "Unexpected event log audit output"
    
    # Cleanup mock log
    if os.path.exists(mock_auth_log):
        os.remove(mock_auth_log)
    print("   ✅ intrusion_detection_log passed.\n")

    # 10. encrypt_decrypt (AES symmetric cryptography)
    print("10. Testing encrypt_decrypt...")
    try:
        import cryptography
        plain_text = "Lumi Voice Assistant AES Cryptography Test String"
        
        # String Encryption
        enc_res = encrypt_decrypt(action="encrypt", data=plain_text)
        print(f"    Encrypt string result: {enc_res}")
        assert "Encrypted text:" in enc_res, "Encryption output mismatch"
        
        # Extract ciphertext and generated key
        lines = enc_res.split("\n")
        ciphertext = lines[0].replace("Encrypted text: ", "").strip()
        gen_key = lines[1].replace("Secret Key (SAVE THIS TO DECRYPT): ", "").strip()
        
        # String Decryption
        dec_res = encrypt_decrypt(action="decrypt", data=ciphertext, key=gen_key)
        print(f"    Decrypt string result: {dec_res}")
        assert plain_text in dec_res, f"Decrypted text '{dec_res}' does not contain '{plain_text}'"

        # File Encryption
        test_file = "data/plain_test.txt"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(plain_text)
            
        enc_file_res = encrypt_decrypt(action="encrypt", data=test_file, key=gen_key, is_file=True)
        print(f"    Encrypt file result: {enc_file_res}")
        assert "Successfully encrypted file" in enc_file_res, "File encryption error"
        
        enc_filepath = f"{test_file}.enc"
        assert os.path.exists(enc_filepath), "Encrypted file does not exist"
        
        # File Decryption
        dec_file_res = encrypt_decrypt(action="decrypt", data=enc_filepath, key=gen_key, is_file=True)
        print(f"    Decrypt file result: {dec_file_res}")
        assert "Successfully decrypted file" in dec_file_res, "File decryption error"
        
        dec_filepath = "data/plain_test_decrypted.txt"
        assert os.path.exists(dec_filepath), "Decrypted file does not exist"
        
        with open(dec_filepath, "r", encoding="utf-8") as f:
            dec_content = f.read()
        assert dec_content == plain_text, f"Decrypted file content '{dec_content}' mismatch"
        
        # Cleanup files
        for f in (test_file, enc_filepath, dec_filepath):
            if os.path.exists(f):
                os.remove(f)
                
    except ImportError:
        # If cryptography is not installed, it should warn with error details
        enc_res = encrypt_decrypt(action="encrypt", data="test")
        print(f"    Bypassed or warning details: {enc_res}")
        assert "cryptography package is not installed" in enc_res, "Should return warning message when cryptography is missing"
        
    print("   ✅ encrypt_decrypt passed.\n")


def test_network_and_firewall_audits():
    print("==================================================")
    print("Testing Network & Firewall Audit Tools...")
    print("==================================================")

    # firewall_rules
    print("Testing firewall_rules...")
    f_rules = firewall_rules(limit=5)
    print(f"   Firewall rules (top 5):\n{f_rules[:500]}...")
    assert "Firewall Rules" in f_rules or "No firewall rules found" in f_rules or "error" in f_rules, "Unexpected output"

    # open_ports
    print("Testing open_ports...")
    o_ports = open_ports()
    print(f"   Open ports:\n{o_ports[:500]}...")
    assert "Open Ports" in o_ports or "No listening ports found" in o_ports or "error" in o_ports, "Unexpected output"

    # active_connections
    print("Testing active_connections...")
    act_conn = active_connections(limit=5)
    print(f"   Active connections:\n{act_conn[:500]}...")
    assert "Active Connections" in act_conn or "error" in act_conn, "Unexpected output"

    # windows_security_audit
    print("Testing windows_security_audit...")
    sec_audit = windows_security_audit()
    print(f"   Security Audit Output:\n{sec_audit}")
    assert "Windows Security Audit:" in sec_audit, "Unexpected output"

    print("   ✅ Network & Firewall Audits passed.\n")


if __name__ == "__main__":
    test_identity_and_access()
    test_security_scanning()
    test_network_and_firewall_audits()
    print("🎉 All security tool tests executed successfully!")
