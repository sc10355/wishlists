######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
TestWishlist API Service Test Suite
"""

# pylint: disable=duplicate-code
import os
import logging
from unittest import TestCase
from datetime import datetime
from wsgi import app
from service.common import status
from service.models import db, Wishlist
from .factories import WishlistFactory, ItemsFactory


DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)
BASE_URL = "/wishlists"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestWishlistService(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Wishlist).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_wishlists(self, count):
        """Factory method to create wishlists in bulk"""
        wishlists = []
        for _ in range(count):
            wishlist = WishlistFactory()
            resp = self.client.post(BASE_URL, json=wishlist.serialize())
            self.assertEqual(
                resp.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Wishlist",
            )
            new_wishlist = resp.get_json()
            wishlist.id = new_wishlist["id"]
            wishlists.append(wishlist)
        return wishlists

    def _create_items(self, wishlist_id, number_of_items):
        """Helper method to create items for a wishlist"""
        items = []
        for _ in range(number_of_items):
            test_item = (
                ItemsFactory()
            )  # Assuming you have ItemFactory to generate item instances
            response = self.client.post(
                f"{BASE_URL}/{wishlist_id}/items",
                json=test_item.serialize(),
                content_type="application/json",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test item",
            )
            new_item = response.get_json()
            test_item.id = new_item["id"]
            items.append(test_item)
        return items

    ######################################################################
    #  P L A C E   T E S T   C A S E S   H E R E
    ######################################################################
    def test_health(self):
        """It should get the health endpoint"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["status"], 200)

    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_create_wishlist(self):
        """It should Create a new Wishlist"""
        test_wishlist = WishlistFactory()
        logging.debug("Test Wishlist: %s", test_wishlist.serialize())
        response = self.client.post(BASE_URL, json=test_wishlist.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_wishlist = response.get_json()
        updated_time_from_response = datetime.strptime(
            new_wishlist["updated_time"], "%a, %d %b %Y %H:%M:%S GMT"
        )

        # Note !
        test_wishlist.id = new_wishlist["id"]

        self.assertEqual(new_wishlist["id"], test_wishlist.id)
        self.assertEqual(new_wishlist["name"], test_wishlist.name)
        self.assertEqual(
            updated_time_from_response.replace(microsecond=0),
            test_wishlist.updated_time.replace(microsecond=0),
        )
        self.assertEqual(new_wishlist["note"], test_wishlist.note)
        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_wishlist = response.get_json()
        self.assertEqual(new_wishlist["id"], test_wishlist.id)
        self.assertEqual(new_wishlist["name"], test_wishlist.name)
        self.assertEqual(
            updated_time_from_response.replace(microsecond=0),
            test_wishlist.updated_time.replace(microsecond=0),
        )
        self.assertEqual(new_wishlist["note"], test_wishlist.note)

    def test_create_items(self):
        """It should Add an item to an wishlist"""
        wishlist = self._create_wishlists(1)[0]
        item = ItemsFactory()
        resp = self.client.post(
            f"{BASE_URL}/{wishlist.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = resp.headers.get("Location", None)
        self.assertIsNotNone(location)

        data = resp.get_json()
        logging.debug(data)

        # The database assign data id automatically, since it is a primary key,
        # so the item response does not match
        item.id = data["id"]

        self.assertEqual(data["name"], item.name)
        self.assertEqual(data["id"], item.id)
        self.assertEqual(data["wishlist_id"], wishlist.id)
        self.assertEqual(data["quantity"], item.quantity)
        self.assertEqual(data["category"], item.category)  # category
        self.assertEqual(data["note"], item.note)

        # Check that the location header was correct by getting it
        resp = self.client.get(location, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_item = resp.get_json()
        self.assertEqual(new_item["name"], item.name, "Address name does not match")

    def test_create_items_wishlist_not_found(self):
        """It should return 404 when the Wishlist is not found"""
        wishlist = self._create_wishlists(1)[0]
        item = ItemsFactory()
        new_wishlist_id = wishlist.id + 1
        resp = self.client.post(
            f"{BASE_URL}/{new_wishlist_id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        # Assert the response status code is 404 NOT FOUND
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_items(self):
        """It should Delete an Items"""
        wishlist = self._create_wishlists(1)[0]
        item = ItemsFactory()
        response = self.client.post(
            f"{BASE_URL}/{wishlist.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        item_id = response.get_json()["id"]

        # delete the item and confirm the deletion
        delete_resp = self.client.delete(f"{BASE_URL}/{wishlist.id}/items/{item_id}")
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)

        get_resp = self.client.get(f"{BASE_URL}/{wishlist.id}/items/{item_id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_items(self):
        """It should Get a single item"""
        # get the id of a item
        wishlist = self._create_wishlists(1)[0]
        test_item = self._create_items(wishlist.id, 1)[0]
        response = self.client.get(f"{BASE_URL}/{wishlist.id}/items/{test_item.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_item.name)

    def test_get_item_not_found(self):
        """It should not Get a item thats not found"""
        wishlist = self._create_wishlists(1)[0]
        response = self.client.get(f"{BASE_URL}/{wishlist.id}/items/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        logging.debug("Response data = %s", data)
        self.assertIn("Wishlist with id '0' could not be found.", data["message"])

    def test_update_wishlist(self):
        """It should Update an existing Wishlist"""
        # create a wishlist to update
        test_wishlist = WishlistFactory()
        response = self.client.post(BASE_URL, json=test_wishlist.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # update the wishlist
        new_wishlist = response.get_json()
        logging.debug(new_wishlist)
        new_wishlist["name"] = "Updated"
        new_wishlist_id = new_wishlist["id"]
        response = self.client.put(f"{BASE_URL}/{new_wishlist_id}", json=new_wishlist)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_wishlist = response.get_json()
        self.assertEqual(updated_wishlist["name"], "Updated")

    def test_delete_wishlist(self):
        """It should Delete a Wishlist"""
        test_wishlist = self._create_wishlists(1)[0]
        response = self.client.delete(f"{BASE_URL}/{test_wishlist.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)
        # make sure they are deleted
        response = self.client.get(f"{BASE_URL}/{test_wishlist.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # READ a wishlist
    def test_get_wishlist(self):
        """It should Read a single wishlist"""
        # get the id of an wishlist
        wishlist = self._create_wishlists(1)[0]
        resp = self.client.get(
            f"{BASE_URL}/{wishlist.id}", content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], wishlist.name)

    def test_get_wishlist_not_found(self):
        """It should not Read an wishlist that is not found"""
        resp = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unsupported_media_type(self):
        """It should not Create when sending unsupported media type"""
        wishlist = WishlistFactory()
        resp = self.client.post(
            BASE_URL, json=wishlist.serialize(), content_type="test/html"
        )
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_wishlist_no_content_type(self):
        """It should not Create a Pet with no content type"""
        response = self.client.post(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_update_wishlist_not_exist(self):
        """It should not Update a Wishlist that does not exist"""
        # create a Wishlist to update
        test_wishlist = WishlistFactory()
        resp = self.client.post(BASE_URL, json=test_wishlist.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # update the wishlist
        new_wishlist = resp.get_json()
        logging.debug(new_wishlist)
        new_wishlist["name"] = "Updated"
        new_wishlist_id = 99999
        resp = self.client.put(f"{BASE_URL}/{new_wishlist_id}", json=new_wishlist)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        negative_wishlist_id = -1
        resp = self.client.put(f"{BASE_URL}/{negative_wishlist_id}", json=new_wishlist)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        invalid_wishlist_id = "asdasdadqwe"
        resp = self.client.put(f"{BASE_URL}/{invalid_wishlist_id}", json=new_wishlist)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_wishlist_item(self):
        """It should Update a wishlist item in a wishlist"""
        # create a known wishlist and wishlist item
        wishlist = self._create_wishlists(1)[0]
        item = ItemsFactory()
        resp = self.client.post(
            f"{BASE_URL}/{wishlist.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        data = resp.get_json()
        logging.debug(data)
        item_id = data["id"]
        data["note"] = "Updated"

        resp = self.client.put(
            f"{BASE_URL}/{wishlist.id}/items/{item_id}",
            json=data,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.client.get(
            f"{BASE_URL}/{wishlist.id}/items/{item_id}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        logging.debug(data)
        self.assertEqual(data["id"], item_id)
        self.assertEqual(data["wishlist_id"], wishlist.id)
        self.assertEqual(data["note"], "Updated")

    def test_update_wishlist_item_not_exist(self):
        """It should not Update a wishlist item that does not exist"""
        wishlist = self._create_wishlists(1)[0]
        item = ItemsFactory()
        resp = self.client.post(
            f"{BASE_URL}/{wishlist.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        data = resp.get_json()
        logging.debug(data)
        item_id = data["id"]
        # Update an item doesn't belongs to that wishlist
        new_item_id = item_id + 1
        data["note"] = "Updated"
        resp = self.client.put(
            f"{BASE_URL}/{wishlist.id}/items/{new_item_id}",
            json=data,
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        new_wishlist_id = 99999
        resp = self.client.put(
            f"{BASE_URL}/{new_wishlist_id}/items/{item_id}",
            json=data,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST LIST*
    # ----------------------------------------------------------
    def test_get_all_wishlist(self):
        """It should Get a list of all Wishlists*"""
        self._create_wishlists(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    # get all items in WL
    def test_get_all_items_in_wishlist(self):
        """It should get/read all items in a wishlist**"""

        wishlist = self._create_wishlists(1)[0]
        resp = self.client.get(
            f"{BASE_URL}/{wishlist.id}", content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        self.assertEqual(data["name"], wishlist.name)
        wishlist.id = data["id"]

        item = ItemsFactory()
        resp = self.client.post(
            f"{BASE_URL}/{wishlist.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(
            f"{BASE_URL}/{wishlist.id}/items",  # Correct endpoint for fetching items
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], item.name)

    def test_data_validation_error(self):
        """It should return a 400 error for invalid data"""
        invalid_data = {"invalid_field": "invalid_value"}
        response = self.client.post(BASE_URL, json=invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_request_method_not_supported(self):
        """It should not Accept any requests with unsupported methods"""
        resp = self.client.post("/", json={}, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
