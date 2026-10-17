import reporting_pdf_ref
import app_pro

app_pro.generate_pdf = reporting_pdf_ref.generate_pdf

if __name__ == "__main__":
    app_pro.CPTApp().mainloop()
