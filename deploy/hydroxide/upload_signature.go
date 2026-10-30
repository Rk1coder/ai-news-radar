package protonmail

import (
	"encoding/base64"
	"io"
	"mime/multipart"
	"strings"
)

func writeAttachmentSignature(w *multipart.Writer, encoded string) error {
	if encoded == "" { return nil }
	part, err := w.CreateFormFile("Signature", "Signature.pgp")
	if err != nil { return err }
	_, err = io.Copy(part, base64.NewDecoder(base64.StdEncoding, strings.NewReader(encoded)))
	return err
}
