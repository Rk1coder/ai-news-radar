FROM golang:1.26-alpine AS build
RUN apk add --no-cache git
WORKDIR /src
# Official Codeberg upstream, pinned to a reviewed revision (2026-10-28).
RUN git init && git remote add origin https://codeberg.org/emersion/hydroxide.git && git fetch --depth 1 origin 02b3b6c8aff726d2404b6ed5f6ba1b7937e1f30e && git checkout --detach FETCH_HEAD
COPY inline-images.patch /tmp/inline-images.patch
COPY attachment-signatures.patch /tmp/attachment-signatures.patch
COPY inline_images.go inline_images_test.go sign_attachments.go sign_attachments_test.go ./smtp/
COPY upload_signature.go upload_signature_test.go ./protonmail/
RUN git apply --check /tmp/inline-images.patch /tmp/attachment-signatures.patch && git apply /tmp/inline-images.patch /tmp/attachment-signatures.patch
RUN go test ./smtp ./protonmail
RUN CGO_ENABLED=0 go build -trimpath -o /hydroxide ./cmd/hydroxide

FROM alpine:3.23
RUN apk add --no-cache ca-certificates && addgroup -g 10001 radar && adduser -D -u 10001 -G radar radar && mkdir -p /data && chown radar:radar /data
COPY --from=build /hydroxide /usr/local/bin/hydroxide
USER radar
ENV XDG_CONFIG_HOME=/data
ENTRYPOINT ["hydroxide"]
CMD ["-smtp-host", "0.0.0.0", "smtp"]
