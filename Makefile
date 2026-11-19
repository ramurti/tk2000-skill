# make kit: build/tk2000-kit.zip, a skill e os guias para quem vai usá-los sem acesso à internet
# (sem os manuais escaneados). Só entram arquivos que estão em commits.
KIT_FILES = .claude-plugin plugin docs examples

kit:
	rm -rf build/kit && mkdir -p build/kit
	git archive --prefix=tk2000-kit/ HEAD $(KIT_FILES) | tar -x -C build/kit
	cp docs/comece-aqui.md build/kit/tk2000-kit/COMECE-AQUI.md
	rm -f build/tk2000-kit.zip
	cd build/kit && zip -qr ../tk2000-kit.zip tk2000-kit
	@echo "build/tk2000-kit.zip: $$(du -h build/tk2000-kit.zip | cut -f1)"

.PHONY: kit
