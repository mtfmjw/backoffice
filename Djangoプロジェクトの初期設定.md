# Djangoプロジェクトの初期設定

Djangoプロジェクトを一から整備する場合に必要な手順のまとめ

## Python環境の初期設定

- Virtual Environmentのインストール

```batch
python -m venv .venv
```

- Virtual Environmentの起動
  
```batch
activate_venv.bat
```

- 必要なパッケージのインストール
  
```batch
pip install -r requirements.txt
```

## Django環境の初期設定

- .env_sampleを.envにコピーする（.envはGitリポジトリに保持しない）

## Dajngo固有テーブルの初期化

[データベースが作成](postgres/データベースの初期設定.md)した後実行すること

```batch
python manage.py migrate
```

## Django Super Userの作成

```batch
set DJANGO_SUPERUSER_USERNAME=admin
set DJANGO_SUPERUSER_EMAIL=backoffice@leadingsoft.co.jp
set DJANGO_SUPERUSER_PASSWORD=P09olp09ol
python manage.py createsuperuser --noinput
```

## Django開発用サーバーの起動

```batch
python manage.py runserver
```
