package smtp

import (
	"bytes"
	"encoding/base64"
	"io"

	"github.com/ProtonMail/go-crypto/openpgp"
	"github.com/emersion/hydroxide/protonmail"
)

// The Proton API requires a detached signature of the unencrypted attachment.
// Radar bounds image payloads before SMTP; prepare the signature before upload.
func signOutgoingAttachment(att *protonmail.Attachment, body io.Reader, signer *openpgp.Entity) (io.Reader, error) {
	data, err := io.ReadAll(body)
	if err != nil { return nil, err }
	var signature bytes.Buffer
	if err := openpgp.DetachSign(&signature, signer, bytes.NewReader(data), nil); err != nil {
		return nil, err
	}
	att.Signature = base64.StdEncoding.EncodeToString(signature.Bytes())
	return bytes.NewReader(data), nil
}
