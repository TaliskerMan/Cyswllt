# Cyswllt Release 0.1.13

This release introduces comprehensive security hardening based on a thorough ShadowAgent security audit, ensuring Cyswllt robustly adheres to the "First, Do No Harm" design principle.

## 🛡️ Security Hardening & Improvements
* **Subprocess Security:** Verified that all `rclone` and `fusermount` invocations utilize list-form arguments, natively preventing shell injection vulnerabilities.
* **Token Handling:** Validated that OAuth token extraction from `rclone authorize` output is handled via secure regex and native JSON parsing without exposing tokens to application logs.
* **Tightened File Permissions:** 
  * Enforced `0o700` strict permissions on the `~/GoogleDrive` local mount directory upon creation.
  * Prevented race conditions during dynamic `.desktop` file generation by using secure `os.open` with `0o700` mode.
  * Secured the logging directory (`~/.cache/cyswllt`) with `0o700` permissions and the log file (`cyswllt.log`) with `0o600` permissions to prevent local privilege escalation and information disclosure.
* **Dependency Analysis:** Included `requirements.txt` to enable future automated Snyk Software Composition Analysis (SCA).

## 📦 Artifacts
Deployed fully according to **ShadowAgent** offline compliance rules:
* Standardized `.deb` compilation archive bounds.
* `sha512sum` hashing metrics attached natively (`checksums.sha512`).
* Detached locally authenticated GPG chain signatures provided natively via the standard Debian `.changes` and `.dsc` structure format.
