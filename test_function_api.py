import asyncio
import httpx
import pytest
import uuid


BASE_URL = "http://localhost:8000"


async def test_function_crud():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        category_name = f"test_category_{uuid.uuid4().hex[:8]}"
        category_response = await client.post(
            "/api/v1/function-categories/",
            json={"name": category_name, "description": "Test category for functions"}
        )
        assert category_response.status_code == 201, f"Failed to create category: {category_response.text}"
        category_data = category_response.json()
        category_id = category_data["id"]
        print(f"Created category: {category_id}")

        function_payload = {
            "name": "customAdd",
            "code": "method customAdd(double a, double b) returns double; return a + b; end;",
            "returnType": "double",
            "signature": [
                {"name": "a", "type": "double", "inOut": False},
                {"name": "b", "type": "double", "inOut": False}
            ],
            "hidden": False
        }

        create_response = await client.post(
            f"/api/v1/function-categories/{category_id}/functions/",
            json=function_payload
        )
        print(f"Create response status: {create_response.status_code}")
        print(f"Create response: {create_response.text}")
        assert create_response.status_code == 201, f"Failed to create function: {create_response.text}"
        function_data = create_response.json()
        function_id = function_data["id"]
        print(f"Created function: {function_id}")

        assert function_data["name"] == "customAdd"
        assert function_data["returnType"] == "double"
        assert len(function_data["signature"]) == 2
        assert function_data["signature"][0]["name"] == "a"
        assert function_data["signature"][0]["type"] == "double"
        assert function_data["signature"][0]["inOut"] == False

        assert "_links" in function_data
        links = function_data["_links"]
        assert "self" in links
        assert "update" in links
        assert "delete" in links
        assert "category" in links
        assert links["self"]["method"] == "GET"
        assert links["update"]["method"] == "PUT"
        assert links["delete"]["method"] == "DELETE"
        assert links["category"]["method"] == "GET"
        assert category_id in links["category"]["href"]

        get_response = await client.get(
            f"/api/v1/function-categories/{category_id}/functions/{function_id}"
        )
        assert get_response.status_code == 200, f"Failed to get function: {get_response.text}"
        get_data = get_response.json()
        assert get_data["id"] == function_id
        assert get_data["name"] == "customAdd"

        list_response = await client.get(
            f"/api/v1/function-categories/{category_id}/functions/"
        )
        assert list_response.status_code == 200, f"Failed to list functions: {list_response.text}"
        list_data = list_response.json()
        assert list_data["total"] >= 1
        assert len(list_data["items"]) >= 1
        assert any(item["id"] == function_id for item in list_data["items"])
        assert "_links" in list_data
        assert "self" in list_data["_links"]
        assert "createFunction" in list_data["_links"]

        update_payload = {
            "name": "customAddUpdated",
            "description": "Updated function"
        }
        update_response = await client.put(
            f"/api/v1/function-categories/{category_id}/functions/{function_id}",
            json=update_payload
        )
        assert update_response.status_code == 200, f"Failed to update function: {update_response.text}"
        update_data = update_response.json()
        assert update_data["name"] == "customAddUpdated"
        assert update_data["version"] == 2

        delete_response = await client.delete(
            f"/api/v1/function-categories/{category_id}/functions/{function_id}"
        )
        assert delete_response.status_code == 204, f"Failed to delete function: {delete_response.text}"

        get_deleted_response = await client.get(
            f"/api/v1/function-categories/{category_id}/functions/{function_id}"
        )
        assert get_deleted_response.status_code == 404

        delete_category_response = await client.delete(
            f"/api/v1/function-categories/{category_id}"
        )
        assert delete_category_response.status_code == 204

        print("All tests passed!")


async def test_function_duplicate_name():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        category_name = f"test_category_{uuid.uuid4().hex[:8]}"
        category_response = await client.post(
            "/api/v1/function-categories/",
            json={"name": category_name, "description": "Test category"}
        )
        assert category_response.status_code == 201
        category_data = category_response.json()
        category_id = category_data["id"]

        function_payload = {
            "name": "testFunc",
            "code": "method testFunc() returns double; return 1.0; end;",
            "returnType": "double"
        }

        create1 = await client.post(
            f"/api/v1/function-categories/{category_id}/functions/",
            json=function_payload
        )
        assert create1.status_code == 201

        create2 = await client.post(
            f"/api/v1/function-categories/{category_id}/functions/",
            json=function_payload
        )
        assert create2.status_code == 400
        assert "already exists" in create2.json()["detail"]

        await client.delete(f"/api/v1/function-categories/{category_id}")
        print("Duplicate name test passed!")


async def test_function_not_found():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        fake_category_id = str(uuid.uuid4())
        fake_function_id = str(uuid.uuid4())

        get_response = await client.get(
            f"/api/v1/function-categories/{fake_category_id}/functions/"
        )
        assert get_response.status_code == 404

        create_response = await client.post(
            f"/api/v1/function-categories/{fake_category_id}/functions/",
            json={
                "name": "test",
                "code": "method test() returns double; return 1.0; end;",
                "returnType": "double"
            }
        )
        assert create_response.status_code == 404

        category_name = f"test_category_{uuid.uuid4().hex[:8]}"
        category_response = await client.post(
            "/api/v1/function-categories/",
            json={"name": category_name}
        )
        category_id = category_response.json()["id"]

        get_function_response = await client.get(
            f"/api/v1/function-categories/{category_id}/functions/{fake_function_id}"
        )
        assert get_function_response.status_code == 404

        await client.delete(f"/api/v1/function-categories/{category_id}")
        print("Not found test passed!")


async def test_function_pagination():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        category_name = f"test_category_{uuid.uuid4().hex[:8]}"
        category_response = await client.post(
            "/api/v1/function-categories/",
            json={"name": category_name}
        )
        category_id = category_response.json()["id"]

        for i in range(5):
            await client.post(
                f"/api/v1/function-categories/{category_id}/functions/",
                json={
                    "name": f"func_{i}",
                    "code": f"method func_{i}() returns double; return {i}.0; end;",
                    "returnType": "double"
                }
            )

        list_response = await client.get(
            f"/api/v1/function-categories/{category_id}/functions/?skip=0&limit=2"
        )
        list_data = list_response.json()
        assert list_data["total"] == 5
        assert list_data["skip"] == 0
        assert list_data["limit"] == 2
        assert len(list_data["items"]) == 2
        assert "next" in list_data["_links"]
        assert "prev" not in list_data["_links"]

        list_response2 = await client.get(
            f"/api/v1/function-categories/{category_id}/functions/?skip=2&limit=2"
        )
        list_data2 = list_response2.json()
        assert len(list_data2["items"]) == 2
        assert "next" in list_data2["_links"]
        assert "prev" in list_data2["_links"]

        list_response3 = await client.get(
            f"/api/v1/function-categories/{category_id}/functions/?skip=4&limit=2"
        )
        list_data3 = list_response3.json()
        assert len(list_data3["items"]) == 1
        assert "next" not in list_data3["_links"]
        assert "prev" in list_data3["_links"]

        await client.delete(f"/api/v1/function-categories/{category_id}")
        print("Pagination test passed!")


if __name__ == "__main__":
    asyncio.run(test_function_crud())
    asyncio.run(test_function_duplicate_name())
    asyncio.run(test_function_not_found())
    asyncio.run(test_function_pagination())
