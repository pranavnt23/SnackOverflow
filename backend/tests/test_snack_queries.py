"""Test Suite: Inventory Listing, Advanced Filtering, Summary, and Status Derivation.

Covers:
8. Listing:
   - Filter by derived status (stocked, running_low, gone).
   - Filter by category enum.
   - Case-insensitive search query with SQL wildcard escaping.
   - SQL pagination with accurate page, page_size, total, and total_pages calculations.
9. Summary:
   - Grouped status counts matching test database records.
   - Snack of the Week resolution (highest votes, ties broken by name ascending, null when unvoted).
10. Status Derivation Boundaries:
   - Exact boundary thresholds: quantity 0 (gone), 1 (running_low), threshold (running_low), threshold+1 (stocked).
"""

from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Snack, SnackCategory, User, Vote


def test_snack_listing_filters_search_and_pagination(
    client: TestClient,
    db_session: Session,
    member_headers: Dict[str, str],
):
    """
    Test 8: Snack Inventory Listing, Filters, Wildcard Escaping, and Pagination.
    """
    # 1. Arrange: Seed a variety of snacks across categories and stock thresholds
    snacks_to_create = [
        Snack(name="Sweet Honey Drops", category=SnackCategory.SWEET, quantity=10, low_stock_threshold=5),       # stocked
        Snack(name="Sweet Gummy Bears", category=SnackCategory.SWEET, quantity=3, low_stock_threshold=5),        # running_low
        Snack(name="Savoury Sea Salt Chips", category=SnackCategory.SAVOURY, quantity=0, low_stock_threshold=5), # gone
        Snack(name="Savoury Cheddar Pretzels", category=SnackCategory.SAVOURY, quantity=8, low_stock_threshold=4),# stocked
        Snack(name="Matcha Green Tea Drink", category=SnackCategory.DRINK, quantity=2, low_stock_threshold=2),   # running_low
        Snack(name="100%_Special Roasted Nuts", category=SnackCategory.HEALTHY_ISH, quantity=0, low_stock_threshold=1), # gone (wildcard test name)
    ]
    db_session.add_all(snacks_to_create)
    db_session.commit()

    # 2. Category Filtering: GET /snacks?category=sweet
    res_cat = client.get("/snacks?category=sweet", headers=member_headers)
    assert res_cat.status_code == 200
    cat_items = res_cat.json()["items"]
    assert len(cat_items) == 2
    assert all(item["category"] == "sweet" for item in cat_items)

    # 3. Status Filtering:
    # 3a. status=stocked -> Sweet Honey Drops (10>5), Savoury Cheddar Pretzels (8>4)
    res_stocked = client.get("/snacks?status=stocked", headers=member_headers)
    assert res_stocked.status_code == 200
    assert res_stocked.json()["total"] == 2
    assert all(item["status"] == "stocked" for item in res_stocked.json()["items"])

    # 3b. status=running_low -> Sweet Gummy Bears (3 in 1..5), Matcha Green Tea Drink (2 in 1..2)
    res_low = client.get("/snacks?status=running_low", headers=member_headers)
    assert res_low.status_code == 200
    assert res_low.json()["total"] == 2
    assert all(item["status"] == "running_low" for item in res_low.json()["items"])

    # 3c. status=gone -> Savoury Sea Salt Chips (0), 100%_Special Roasted Nuts (0)
    res_gone = client.get("/snacks?status=gone", headers=member_headers)
    assert res_gone.status_code == 200
    assert res_gone.json()["total"] == 2
    assert all(item["status"] == "gone" for item in res_gone.json()["items"])

    # 4. Search with case-insensitive partial match
    res_search = client.get("/snacks?search=cheddar", headers=member_headers)
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["name"] == "Savoury Cheddar Pretzels"

    # 5. Wildcard Escaping: Search literal string containing "%" and "_"
    res_wildcard = client.get("/snacks?search=100%_", headers=member_headers)
    assert res_wildcard.status_code == 200
    assert res_wildcard.json()["total"] == 1
    assert res_wildcard.json()["items"][0]["name"] == "100%_Special Roasted Nuts"

    # 6. Pagination validation (total 6 items, page_size 2 -> 3 total pages)
    # Page 1
    p1 = client.get("/snacks?page=1&page_size=2", headers=member_headers).json()
    assert len(p1["items"]) == 2
    assert p1["page"] == 1
    assert p1["page_size"] == 2
    assert p1["total"] == 6
    assert p1["total_pages"] == 3

    # Page 2
    p2 = client.get("/snacks?page=2&page_size=2", headers=member_headers).json()
    assert len(p2["items"]) == 2
    assert p2["page"] == 2

    # Page 3
    p3 = client.get("/snacks?page=3&page_size=2", headers=member_headers).json()
    assert len(p3["items"]) == 2
    assert p3["page"] == 3

    # Ensure no duplicates across paginated results
    all_names = [i["name"] for i in p1["items"] + p2["items"] + p3["items"]]
    assert len(set(all_names)) == 6


def test_summary_counts_and_snack_of_the_week(
    client: TestClient,
    db_session: Session,
    member_headers: Dict[str, str],
    admin_user: User,
    member_user: User,
):
    """
    Test 9: Summary Statistics and Snack of the Week.
    
    Verifies that:
    1. Grouped counts {stocked, running_low, gone, total} are accurately calculated in SQL.
    2. Before any votes, snack_of_the_week is null.
    3. Voting establishes the correct Snack of the Week based on vote count.
    4. Equal vote ties are broken alphabetically by name ascending.
    """
    # 1. Arrange: Create snacks
    snack_a = Snack(name="Apple Crisp Chips", category=SnackCategory.HEALTHY_ISH, quantity=10, low_stock_threshold=4) # stocked
    snack_b = Snack(name="Banana Coconut Muffin", category=SnackCategory.SWEET, quantity=2, low_stock_threshold=4)    # running_low
    snack_c = Snack(name="Caramel Popcorn", category=SnackCategory.SWEET, quantity=0, low_stock_threshold=3)          # gone
    db_session.add_all([snack_a, snack_b, snack_c])
    db_session.commit()

    # 2. Check summary before any votes exist
    res_init = client.get("/snacks/summary", headers=member_headers)
    assert res_init.status_code == 200
    data_init = res_init.json()
    assert data_init["stocked"] == 1
    assert data_init["running_low"] == 1
    assert data_init["gone"] == 1
    assert data_init["total"] == 3
    assert data_init["snack_of_the_week"] is None

    # 3. Cast 1 vote for Banana Coconut Muffin
    vote_1 = Vote(user_id=member_user.id, snack_id=snack_b.id)
    db_session.add(vote_1)
    db_session.commit()

    res_voted = client.get("/snacks/summary", headers=member_headers)
    assert res_voted.status_code == 200
    sotw = res_voted.json()["snack_of_the_week"]
    assert sotw is not None
    assert sotw["id"] == snack_b.id
    assert sotw["vote_count"] == 1

    # 4. Tie-breaking test: Admin votes for Apple Crisp Chips (both have 1 vote now)
    # Alphabetical order: "Apple Crisp Chips" comes before "Banana Coconut Muffin"
    vote_2 = Vote(user_id=admin_user.id, snack_id=snack_a.id)
    db_session.add(vote_2)
    db_session.commit()

    res_tied = client.get("/snacks/summary", headers=member_headers)
    assert res_tied.status_code == 200
    sotw_tied = res_tied.json()["snack_of_the_week"]
    assert sotw_tied is not None
    assert sotw_tied["id"] == snack_a.id, "Tie must be broken by snack name ascending (Apple < Banana)"
    assert sotw_tied["name"] == "Apple Crisp Chips"
    assert sotw_tied["vote_count"] == 1


def test_status_derivation_boundaries(
    client: TestClient,
    db_session: Session,
    member_headers: Dict[str, str],
):
    """
    Test 10: Status Derivation Boundary Invariants.
    
    Status is strictly derived via SQL CASE expression:
      - gone: quantity == 0
      - running_low: 1 <= quantity <= low_stock_threshold
      - stocked: quantity > low_stock_threshold
    
    Tests exact boundary transitions at threshold = 5:
      - quantity = 0 -> 'gone'
      - quantity = 1 -> 'running_low'
      - quantity = 5 (quantity == threshold) -> 'running_low'
      - quantity = 6 (quantity == threshold + 1) -> 'stocked'
    """
    # 1. Arrange: Create 4 snacks representing boundary values
    threshold = 5
    snack_zero = Snack(name="Boundary Snack Zero", category=SnackCategory.SAVOURY, quantity=0, low_stock_threshold=threshold)
    snack_one = Snack(name="Boundary Snack One", category=SnackCategory.SAVOURY, quantity=1, low_stock_threshold=threshold)
    snack_thresh = Snack(name="Boundary Snack Thresh", category=SnackCategory.SAVOURY, quantity=5, low_stock_threshold=threshold)
    snack_plus_one = Snack(name="Boundary Snack Plus One", category=SnackCategory.SAVOURY, quantity=6, low_stock_threshold=threshold)

    db_session.add_all([snack_zero, snack_one, snack_thresh, snack_plus_one])
    db_session.commit()

    # 2. Query each by ID to check single item response status
    res_zero = client.get(f"/snacks/{snack_zero.id}", headers=member_headers)
    assert res_zero.status_code == 200
    assert res_zero.json()["status"] == "gone"

    res_one = client.get(f"/snacks/{snack_one.id}", headers=member_headers)
    assert res_one.status_code == 200
    assert res_one.json()["status"] == "running_low"

    res_thresh = client.get(f"/snacks/{snack_thresh.id}", headers=member_headers)
    assert res_thresh.status_code == 200
    assert res_thresh.json()["status"] == "running_low"

    res_plus_one = client.get(f"/snacks/{snack_plus_one.id}", headers=member_headers)
    assert res_plus_one.status_code == 200
    assert res_plus_one.json()["status"] == "stocked"

    # 3. Query list endpoint to ensure SQL CASE filtering works across all 4 boundaries
    list_res = client.get("/snacks?page_size=10", headers=member_headers).json()["items"]
    status_map = {item["name"]: item["status"] for item in list_res}

    assert status_map["Boundary Snack Zero"] == "gone"
    assert status_map["Boundary Snack One"] == "running_low"
    assert status_map["Boundary Snack Thresh"] == "running_low"
    assert status_map["Boundary Snack Plus One"] == "stocked"
