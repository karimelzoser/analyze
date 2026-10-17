import reporting_pdf_ref_v2
import app_pro

# Keep the full professional desktop UI and Excel engine, but route PDF
# generation through the final reference-style renderer.
app_pro.generate_pdf = reporting_pdf_ref_v2.generate_pdf

if __name__ == "__main__":
    app_pro.CPTApp().mainloop()
