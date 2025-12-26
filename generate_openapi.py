"""生成 OpenAPI JSON 文档"""

from fastapi.openapi.utils import get_openapi
from json import dumps
from api.app import app


def generate_openapi_json():
    """生成 OpenAPI JSON 文档"""
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    with open("openapi.json", "w", encoding="utf-8") as f:
        f.write(dumps(openapi_schema, ensure_ascii=False, indent=2))
    
    print("✅ OpenAPI 文档已生成: openapi.json")


if __name__ == "__main__":
    generate_openapi_json()
