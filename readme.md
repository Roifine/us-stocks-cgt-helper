# 🇦🇺 Australian CGT Calculator - Streamlit App

A web application for calculating optimized Australian Capital Gains Tax from Interactive Brokers HTML statements.

## 🚀 Quick Start

### Local Development

1. **Clone/Download** your files to a folder:
```
cgt_app/
├── app.py                          # Main Streamlit app
├── html_to_cost_basis.py          # Your existing Script 1
├── cgt_calculator_australia.py    # Your existing Script 2
├── requirements.txt               # Dependencies
└── README.md                      # This file
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the app:**
```bash
streamlit run app.py
```

4. **Open browser** to: `http://localhost:8501`

### Deploy to Streamlit Cloud (Free)

1. **Create GitHub repository** with your files
2. **Go to** [share.streamlit.io](https://share.streamlit.io)
3. **Connect** your GitHub account
4. **Deploy** from your repository
5. **Share** the generated URL

## 📋 How to Use

1. **Upload** up to 5 Interactive Brokers HTML statement files
2. **Select** your financial year (Australian: July 1 - June 30)
3. **Click** "Process Files" 
4. **Download** your optimized Australian CGT report

## ✨ Features

- ✅ **Tax Optimized**: Prioritizes long-term holdings for 50% CGT discount
- ✅ **Multiple Files**: Process up to 5 HTML statements at once
- ✅ **Secure**: Files processed in memory, not stored
- ✅ **Australian CGT**: Follows Australian tax rules and regulations
- ✅ **Excel Output**: Ready for tax lodgment

## 🔧 Requirements

- Python 3.8+
- Interactive Brokers HTML statements
- Internet connection (for Streamlit Cloud deployment)

## 📄 Output

The app generates an Excel file with:
- Detailed CGT calculations for each sale
- Tax optimization (long-term vs short-term)
- Summary sheet with totals
- Warnings for any issues

## ⚠️ Important Notes

- This tool is for informational purposes only
- Always consult a qualified tax professional
- Verify calculations before tax lodgment
- Files are processed temporarily and not stored

## 🆘 Troubleshooting

**App won't start?**
- Check that both Python scripts are in the same folder
- Install requirements: `pip install -r requirements.txt`

**Processing fails?**
- Ensure HTML files are from Interactive Brokers
- Check file size (max 20MB per file)
- Try with fewer files first

**No sales found?**
- Verify the correct financial year is selected
- Check that HTML files contain the expected date range

## 📞 Support

If you encounter issues:
1. Check the warning messages in the app
2. Try with a single HTML file first
3. Verify your HTML files are valid Interactive Brokers statements