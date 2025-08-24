### Next Backend Steps for Multi-Supplier Fulfillment

- OrderItem fields added:
  - supplier (FK), supplier_price (decimal), fulfillment_source ('supplier' | 'internal')
  - created_by already added on Order
- To implement next:
  1) Auto-assign default supplier at order creation (best price/available) if not provided.
  2) Create Supplier Purchase Orders grouped by supplier per order:
     - Models: SupplierPurchaseOrder(supplier, status, eta, notes), SupplierPOItem(po, product, qty, price, linked_order_item)
     - Endpoints:
       - POST /api/procurement/purchase-orders/ (from order id; auto-generate)
       - GET/PATCH /api/procurement/purchase-orders/{id}/
       - POST /api/procurement/purchase-orders/{id}/receive/ (partial allowed)
  3) For fulfillment_source='internal':
     - Create ProductionReservation(order_item_id, product_id, qty)
     - On batch completion, fulfill reservations and update finished inventory
  4) Extend serializers to expose supplier grouping on orders
  5) Permissions: only staff/admin can create POs; customers read-only

Migration commands:
```bash
cd /Users/jodybeggs/Documents/fambrifarms_after_meeting/backend
source venv/bin/activate
python manage.py makemigrations accounts orders
python manage.py migrate
```

### Superuser-exclusive management (roadmap and endpoints)

- Global access control
  - Create/upgrade/downgrade users (including superusers); set staff roles[]; deactivate/reactivate any account
  - Force password resets; rotate API keys/allowed origins; environment toggles
  - Endpoints (admin-only):
    - GET/POST /api/admin/users/
    - PATCH /api/admin/users/{id}/ (roles, active, phone, names)
    - POST /api/admin/users/{id}/reset_password/

- Restaurant membership & ownership
  - Create/update restaurants; assign/remove users with restaurant_roles[] (chef/manager/owner/staff)
  - Endpoints:
    - GET/POST /api/admin/restaurants/
    - POST /api/admin/restaurants/{id}/add_user/
    - DELETE /api/admin/restaurants/{id}/remove_user/{userId}/

- Catalog & pricing guardrails
  - Change VAT rate, payment terms; set preferred supplier rules; approve price overrides over threshold

- Procurement & production authority
  - Approve/revoke supplier contracts, PO limits; override lead times; cancel POs; force-complete production batches (with audit)

- Financial controls
  - Void invoices, issue credits above threshold, write-offs (with audit trail)

- Data operations
  - Anonymize/delete data on request; export data; schedule backups
