import app_modern
import app_pdf_enabled
import reporting_export_v2

# Production wiring:
# - five-column engineering workbook exporter
# - modern maximized desktop shell
# - reliable latest-workbook opening
# - mixed GEF/GFF/PDF input with raw-source preference
# - validated native-vector PDF analysis and appended PDF summary pages
app_modern.export_excel = reporting_export_v2.export_excel


if __name__ == "__main__":
    app_pdf_enabled.PDFEnabledCPTApp().mainloop()
