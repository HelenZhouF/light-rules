import asyncio
import uuid
import os
import tempfile

# Use a temporary file database to avoid locking issues
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db.close()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{temp_db.name}"

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base
from app.models import *


async def test_function_category_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("=" * 60)
        print("Testing Function Category CRUD API")
        print("=" * 60)

        expected_media_type = "application/vnd.sas.business.rule.function.category"
        expected_list_media_type = "application/vnd.sas.business.rule.function.category.list"

        print("\n1. Test Create FunctionCategory (POST /api/v1/function-categories/)")
        create_data = {
            "name": "Test Category",
            "description": "This is a test category",
            "hidden": False
        }
        response = await client.post("/api/v1/function-categories/", json=create_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        data = response.json()
        category_id = data["id"]
        print(f"   Created category ID: {category_id}")
        
        # Verify new field names
        assert "creationTimeStamp" in data, "creationTimeStamp field missing"
        assert "modifiedTimeStamp" in data, "modifiedTimeStamp field missing"
        assert "created_datetime" not in data, "created_datetime should not be present"
        assert "modified_datetime" not in data, "modified_datetime should not be present"
        print("   Field names verified: creationTimeStamp, modifiedTimeStamp")
        
        # Verify HATEOAS links format
        assert "_links" in data
        for link_name in ["self", "update", "delete"]:
            assert link_name in data["_links"], f"{link_name} link missing"
            link = data["_links"][link_name]
            assert "href" in link, f"{link_name} href missing"
            assert "method" in link, f"{link_name} method missing"
            assert "uri" in link, f"{link_name} uri missing"
            assert "type" in link, f"{link_name} type missing"
            assert link["uri"] == link["href"], f"{link_name} uri should equal href"
            assert link["type"] == expected_media_type, f"{link_name} type incorrect"
        print("   HATEOAS links verified: href, method, uri, type present")

        print("\n2. Test Get FunctionCategory (GET /api/v1/function-categories/{id})")
        response = await client.get(f"/api/v1/function-categories/{category_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["name"] == "Test Category"
        assert data["description"] == "This is a test category"
        assert data["hidden"] == False
        assert "creationTimeStamp" in data
        assert "modifiedTimeStamp" in data
        
        # Verify HATEOAS links
        for link_name in ["self", "update", "delete"]:
            link = data["_links"][link_name]
            assert link["uri"] == link["href"]
            assert link["type"] == expected_media_type
        print("   Single resource HATEOAS verified")

        print("\n3. Test Update FunctionCategory (PUT /api/v1/function-categories/{id})")
        update_data = {
            "name": "Updated Test Category",
            "description": "This is an updated test category",
            "hidden": True
        }
        response = await client.put(f"/api/v1/function-categories/{category_id}", json=update_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["name"] == "Updated Test Category"
        assert data["description"] == "This is an updated test category"
        assert data["hidden"] == True
        assert data["version"] == 2
        assert "creationTimeStamp" in data
        assert "modifiedTimeStamp" in data
        print("   Update verified")

        print("\n4. Test List FunctionCategories (GET /api/v1/function-categories/)")
        response = await client.get("/api/v1/function-categories/")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Total: {data['total']}, Items count: {len(data['items'])}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "_links" in data
        assert "self" in data["_links"]
        assert "createFunctionCategory" in data["_links"]
        
        # Verify list links HATEOAS format
        list_self_link = data["_links"]["self"]
        assert "uri" in list_self_link
        assert "type" in list_self_link
        assert list_self_link["uri"] == list_self_link["href"]
        assert list_self_link["type"] == expected_list_media_type
        
        # Verify createFunctionCategory link
        create_link = data["_links"]["createFunctionCategory"]
        assert "uri" in create_link
        assert "type" in create_link
        assert create_link["uri"] == create_link["href"]
        assert create_link["type"] == expected_media_type
        print("   List HATEOAS verified")

        print("\n5. Test List with include_hidden=true")
        response = await client.get("/api/v1/function-categories/?include_hidden=true")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Total (including hidden): {data['total']}")
        assert response.status_code == 200

        print("\n6. Test Delete FunctionCategory (DELETE /api/v1/function-categories/{id})")
        response = await client.delete(f"/api/v1/function-categories/{category_id}")
        print(f"   Status: {response.status_code}")
        assert response.status_code == 204, f"Expected 204, got {response.status_code}"
        print("   Delete verified")

        print("\n7. Verify deleted category returns 404")
        response = await client.get(f"/api/v1/function-categories/{category_id}")
        print(f"   Status: {response.status_code}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("   404 verified")

        print("\n8. Test duplicate name prevention")
        create_data1 = {"name": "Unique Category"}
        create_data2 = {"name": "Unique Category"}
        response1 = await client.post("/api/v1/function-categories/", json=create_data1)
        response2 = await client.post("/api/v1/function-categories/", json=create_data2)
        print(f"   First create status: {response1.status_code}")
        print(f"   Second create status: {response2.status_code}")
        assert response1.status_code == 201
        assert response2.status_code == 400
        print("   Duplicate name prevention verified")

        print("\n" + "=" * 60)
        print("All tests passed! ✅")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_function_category_crud())
