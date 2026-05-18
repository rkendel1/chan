# Docker Runtime Warnings

This document explains common warnings you may see when running the Chandra OCR service in Docker and how to address them.

## pypdfium2 XFA Support Warning

### Warning Message
```
WARNING:pypdfium2._helpers.document:init_forms() called on XFA pdf, but this pdfium binary was compiled without XFA support.
Run `PDFIUM_PLATFORM=auto-v8 pip install -v pypdfium2 --no-binary pypdfium2` to get a build with XFA support.
```

### What It Means
- This warning appears when processing **XFA (XML Forms Architecture) PDFs** - a specific Adobe PDF form type
- The default pypdfium2 binary doesn't include XFA support
- Regular PDFs and most PDF forms work fine without XFA support

### When You Need XFA Support
XFA PDFs are relatively rare. You only need XFA support if:
- You're specifically processing XFA-enabled PDF forms
- Users report form fields not being extracted correctly
- Your PDFs were created with Adobe LiveCycle Designer or similar XFA tools

### How to Enable XFA Support

#### Option 1: Uncomment in Dockerfile (Recommended for production)
Edit the `Dockerfile` and uncomment the XFA support line:

```dockerfile
# Optional: Install pypdfium2 with XFA support for XFA-enabled PDF forms
# XFA (XML Forms Architecture) is an Adobe PDF form type - uncomment if needed
# Note: This increases build time as it compiles pypdfium2 from source with v8
RUN PDFIUM_PLATFORM=auto-v8 pip install -v pypdfium2==4.30.0 --no-binary pypdfium2 --force-reinstall
```

Then rebuild the Docker image:
```bash
docker-compose build
```

**Trade-offs:**
- ✅ Enables XFA form processing
- ✅ Permanent solution in the image
- ⚠️ Increases build time significantly (compiles from source with v8 JavaScript engine)
- ⚠️ Slightly larger image size

#### Option 2: Install at runtime (for testing)
Run inside the container:
```bash
docker-compose exec chandra bash
PDFIUM_PLATFORM=auto-v8 pip install -v pypdfium2==4.30.0 --no-binary pypdfium2 --force-reinstall
```

This is temporary and will be lost when the container is recreated.

### Recommendation
**For most use cases, you can safely ignore this warning.** Only enable XFA support if you specifically need to process XFA PDF forms.

---

## Transformers processor_kwargs Warning

### Warning Message
```
[transformers] Kwargs passed to `processor.__call__` have to be in processor_kwargs dict, not in `**kwargs`
```

### What It Means
- This is a **cosmetic warning** from the transformers library (version 5.2.0+)
- It's an internal deprecation warning from the library itself
- The warning appears during internal transformers code execution, not from application code

### Impact
- **None** - The system functions correctly despite this warning
- The application code already uses the correct API
- Future versions of transformers will likely eliminate this warning internally

### Action Required
**No action needed.** This is a library-internal warning that doesn't affect functionality.

---

## Summary

| Warning | Severity | Action Required |
|---------|----------|-----------------|
| pypdfium2 XFA | Low | Only if processing XFA PDFs (rare) |
| transformers processor_kwargs | None | No action needed |

Both warnings are informational and don't prevent the service from working correctly. The system processes regular PDFs and most PDF forms without issues.
