# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a lead database automation tool that processes business card images and hearing sheets, extracts information using OCR, and automatically registers data to a Notion database. The system also generates Gmail drafts for follow-up communication.

## Architecture

The system consists of two main phases (separated in feature/separate branch):

1. **Notion Registration Phase** (`src/notion_sever/`):
   - Web server for uploading business card/hearing sheet images
   - OCR processing using GPT-4o for text extraction
   - Data processing and Notion database registration
   - Image hosting on remote server

2. **Gmail Generation Phase** (`src/gmail/`):
   - Retrieves data from Notion database
   - Generates email content using Gemini
   - Creates Gmail drafts via Gmail API

## Environment Setup

### Using pyenv:
```bash
pip install pyenv==2.5.0
pyenv install 3.12.6
pyenv virtualenv 3.12.6 NotionBizCard
pyenv activate NotionBizCard
pip install --upgrade pip==25.0.1
pip install -r requirement.txt
```

### Using conda:
```bash
conda env create -f environment.yml
```

## Development Commands

### Start Web Server:
```bash
cd src/notion_sever
python sever.py
```
Access at: http://127.0.0.1:5001

### Generate Gmail Drafts:
```bash
cd src/gmail
python main.py
```

## Configuration

- `config.ini`: Contains API keys, database IDs, and server settings
  - `[HOST]` section: Production configuration with mocomoco database
  - `[LOCAL]` section: Development/testing configuration
- SSH key path must be configured for remote image server uploads

## Key Components

### OCR Processing (`ocr.py`):
- Uses GPT-4o for business card text extraction
- Predefined lists for industry, department, and position classification
- Returns structured JSON with extracted information

### Notion Integration (`creteNotionPerties.py`):
- Maps extracted data to Notion database properties
- Handles field type conversions (title, rich_text, select, multi_select, etc.)
- Persona calculation based on BANT scoring

### Image Processing:
- Converts uploaded images to JPEG format
- Resizes to 512x512 for optimization
- Uploads to remote server for public URL access

### Web Interface (`sever.py`):
- Flask application with form handling
- File upload and validation
- Handover functionality for lead transfer between team members

## Database Schema

Current Notion database fields:
- 会社名 (title)
- 担当者氏名, 部署名, 役職名 (rich_text)
- 電話番号 (phone_number), メール (email)
- リード獲得日, 契約開始日 (date)
- 担当, 製品, ステータス (multi_select)
- ペルソナ, タグ (select)
- ヒアリングメモ, ボイレコ貸し出し (rich_text)

## Branch Strategy

- `main`: Main stable branch
- `develop`: Development branch
- `feature/separate`: Current working branch with separated processing phases