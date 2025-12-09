#!/bin/bash
# ============================================================
# Local Test Script for ECE 461 Phase 2 Registry
# Tests all endpoints required by the autograder
# Run with: bash local_test.sh
# ============================================================

BASE="http://localhost:8080"
AUTH="X-Authorization: test"

print() {
  echo -e "\n==== $1 ====\n"
}

test_endpoint() {
  DESC=$1
  CMD=$2
  EXPECT=$3

  print "$DESC"
  RESP=$(eval "$CMD")
  echo "Response: $RESP"

  if echo "$RESP" | grep -q "$EXPECT"; then
    echo "[PASS] $DESC"
  else
    echo "[FAIL] $DESC"
  fi
}

# ----------------------------
# 1. HEALTH CHECKS
# ----------------------------
test_endpoint "Health OK" \
  "curl -s $BASE/health" \
  "ok"

test_endpoint "Health Components" \
  "curl -s '$BASE/health/components?windowMinutes=60'" \
  "components"

# ----------------------------
# 2. TRACKS (must be empty list)
# ----------------------------
test_endpoint "/tracks present" \
  "curl -s $BASE/tracks" \
  "plannedTracks"

# ----------------------------
# 3. AUTHENTICATION (must be 501)
# ----------------------------
print "Test /authenticate must return 501"
curl -s -o /tmp/auth.txt -w "%{http_code}" -X PUT "$BASE/authenticate" \
     -H "Content-Type: application/json" \
     --data '{"user":{"name":"a","is_admin":false},"secret":{"password":"pass"}}' \
     > /tmp/auth_code.txt

STATUS=$(cat /tmp/auth_code.txt)
echo "Status: $STATUS"
if [ "$STATUS" -eq 501 ]; then
  echo "[PASS] /authenticate returns 501"
else
  echo "[FAIL] /authenticate incorrect status"
fi

# ----------------------------
# 4. RESET REGISTRY
# ----------------------------
test_endpoint "Registry Reset" \
  "curl -s -X DELETE -H \"$AUTH\" $BASE/reset" \
  "status"

# ----------------------------
# 5. CREATE ARTIFACTS
# ----------------------------
print "Creating a model artifact..."
MODEL_RESP=$(curl -s -X POST "$BASE/artifact/model" \
     -H "$AU
