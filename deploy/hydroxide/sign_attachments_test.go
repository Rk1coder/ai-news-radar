package smtp

import (
	"bytes"
	"encoding/base64"
	"io"
	"testing"

	"github.com/ProtonMail/go-crypto/openpgp"
	"github.com/emersion/hydroxide/protonmail"
)

func TestAttachmentSignatureVerifiesExactImageBytes(t *testing.T) {
	key, err := openpgp.NewEntity("Radar test", "", "test@example.com", nil)
	if err != nil { t.Fatal(err) }
	data := []byte("\x89PNG\r\n\x1a\nimage payload")
	att := &protonmail.Attachment{}
	r, err := signOutgoingAttachment(att, bytes.NewReader(data), key)
	if err != nil { t.Fatal(err) }
	got, err := io.ReadAll(r)
	if err != nil || !bytes.Equal(got, data) { t.Fatal("attachment bytes changed") }
	sig, err := base64.StdEncoding.DecodeString(att.Signature)
	if err != nil { t.Fatal(err) }
	if _, err := openpgp.CheckDetachedSignature(openpgp.EntityList{key}, bytes.NewReader(data), bytes.NewReader(sig), nil); err != nil {
		t.Fatal(err)
	}
	if _, err := openpgp.CheckDetachedSignature(openpgp.EntityList{key}, bytes.NewReader([]byte("changed")), bytes.NewReader(sig), nil); err == nil {
		t.Fatal("signature accepted changed bytes")
	}
}
