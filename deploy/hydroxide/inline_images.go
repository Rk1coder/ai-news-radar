package smtp

import (
	"strings"

	"github.com/emersion/go-message/mail"
)

// go-message categorizes Content-Disposition:inline images as body parts.
// Hydroxide's body handler ignores them after HTML has been read. Route CID
// images through its encrypted attachment uploader instead, preserving their
// original Content-ID and inline disposition for Proton's HTML rendering.
func normalizeInlineImagePart(p *mail.Part) {
	h, ok := p.Header.(*mail.InlineHeader)
	if !ok || h.Get("Content-ID") == "" {
		return
	}
	mediaType, _, err := h.ContentType()
	if err == nil && strings.HasPrefix(mediaType, "image/") {
		p.Header = &mail.AttachmentHeader{Header: h.Header}
	}
}

// MIME encloses Content-ID in brackets; the Proton upload API expects the
// unwrapped identifier, exactly as referenced after cid: in the HTML.
func protonContentID(value string) string {
	return strings.Trim(value, " <>")
}
