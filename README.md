```sh
brew install redis
brew services start redis
```

```sh
uv run uvicorn app:app --reload
```
```
curl -X POST "http://localhost:8000/audio" \
     -H "Content-Type: application/json" \
     -d '{"kind":"general","audio_base64":"<some_base64>"}'
``` 