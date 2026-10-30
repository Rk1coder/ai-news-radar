package protonmail

import (
	"bytes"
	"encoding/base64"
	"io"
	"mime/multipart"
	"testing"
)

func TestSignatureIsUploadedAsBinaryMultipartField(t *testing.T) {
	var b bytes.Buffer
	w := multipart.NewWriter(&b)
	signature := []byte{0, 1, 2, 128, 255}
	if err := writeAttachmentSignature(w, base64.StdEncoding.EncodeToString(signature)); err != nil { t.Fatal(err) }
	if err := w.Close(); err != nil { t.Fatal(err) }
	r := multipart.NewReader(&b, w.Boundary())
	p, err := r.NextPart()
	if err != nil { t.Fatal(err) }
	data, err := io.ReadAll(p)
	if err != nil || p.FormName() != "Signature" || !bytes.Equal(data, signature) {
		t.Fatal("binary signature field missing or changed")
	}
}
