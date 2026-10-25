# API

V1 API conventions:

## Success

```json
{
  "data": {},
  "meta": {}
}
```

## Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable explanation",
    "details": []
  }
}
```

Collection endpoints will support pagination, filtering and sorting. Side-effect commands must validate the complete workflow before committing changes.
