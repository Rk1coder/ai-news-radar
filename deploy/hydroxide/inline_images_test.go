package smtp

import (
	"io"
	"strings"
	"testing"

	"github.com/emersion/go-message/mail"
)

func TestInlineImagesReachAttachmentUploader(t *testing.T) {
	// The same related/alternative structure used by Radar's Python sender.
	fixture := "MIME-Version: 1.0\r\nContent-Type: multipart/related; boundary=outer\r\n\r\n" +
		"--outer\r\nContent-Type: multipart/alternative; boundary=inner\r\n\r\n" +
		"--inner\r\nContent-Type: text/plain\r\n\r\nRadar\r\n" +
		"--inner\r\nContent-Type: text/html\r\n\r\n<img src=\"cid:radar-logo\"><img src=\"cid:cover\">\r\n--inner--\r\n" +
		"--outer\r\nContent-Type: image/png\r\nContent-Disposition: inline; filename=radar-logo.png\r\nContent-ID: <radar-logo>\r\nContent-Transfer-Encoding: base64\r\n\r\nbG9nby1ieXRlcw==\r\n" +
		"--outer\r\nContent-Type: image/jpeg\r\nContent-Disposition: inline; filename=cover.jpeg\r\nContent-ID: <cover>\r\nContent-Transfer-Encoding: base64\r\n\r\nY292ZXItYnl0ZXM=\r\n--outer--\r\n"
	r, err := mail.CreateReader(strings.NewReader(fixture))
	if err != nil { t.Fatal(err) }
	defer r.Close()
	attachments := map[string]string{}
	bodyParts := 0
	for {
		p, err := r.NextPart()
		if err == io.EOF { break }
		if err != nil { t.Fatal(err) }
		normalizeInlineImagePart(p)
		data, err := io.ReadAll(p.Body)
		if err != nil { t.Fatal(err) }
		switch h := p.Header.(type) {
		case *mail.InlineHeader:
			bodyParts++
		case *mail.AttachmentHeader:
			attachments[h.Get("Content-ID")] = string(data)
			if disposition, _, _ := h.ContentDisposition(); disposition != "inline" {
				t.Fatal("original inline disposition was changed")
			}
			if filename, _ := h.Filename(); filename == "" { t.Fatal("filename lost") }
		}
	}
	if bodyParts != 2 || len(attachments) != 2 || attachments["<radar-logo>"] != "logo-bytes" || attachments["<cover>"] != "cover-bytes" {
		t.Fatalf("body parts=%d, images=%v", bodyParts, attachments)
	}
}

func TestNormalAttachmentRemainsUnchanged(t *testing.T) {
	r, err := mail.CreateReader(strings.NewReader("Content-Type: application/pdf\r\nContent-Disposition: attachment; filename=report.pdf\r\n\r\npdf"))
	if err != nil { t.Fatal(err) }
	defer r.Close()
	p, err := r.NextPart()
	if err != nil { t.Fatal(err) }
	before := p.Header
	normalizeInlineImagePart(p)
	if p.Header != before { t.Fatal("ordinary attachment was changed") }
}

func TestProtonContentIDMatchesHTMLReference(t *testing.T) {
	for _, value := range []string{"<logo@radar.local>", "logo@radar.local", " <logo@radar.local> "} {
		if got := protonContentID(value); got != "logo@radar.local" {
			t.Fatalf("API ContentID = %q", got)
		}
	}
	if protonContentID("") != "" { t.Fatal("missing CID must stay empty") }
}
