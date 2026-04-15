tokenAdmin="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6ImFkbWluQGdtYWlsLmNvbSIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3NjMwNjExMX0.gOfgo0Z3RgfrBXQ79RD8r1tZchhEhX3yp5JSjKDNEXU"
tokenManager="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjozLCJlbWFpbCI6InJvZ2Vyc2FudGlhZ29taEB1ZnBzLmVkdS5jbyIsInJvbGUiOiJtYW5hZ2VyIiwiZXhwIjoxNzc2MzA2MTU2fQ.kSghDFotY2HrYiLj7ZXpzS-mB9XHWjeU7qjAZEfyocc"
tokenWorker="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0LCJlbWFpbCI6ImphaWRlcnJpY2FyZG9jZkB1ZnBzLmVkdS5jbyIsInJvbGUiOiJ3b3JrZXIiLCJleHAiOjE3NzYzMDYxODN9.qE8xHsE2iZEGii7hfy_4hnk6v9Em9uDcPOFeIehuuUg"

#curl -X POST http://localhost:8000/auth/logout/ \
#  -H "Authorization: Bearer $tokenAdmin"

#curl -X POST http://localhost:8000/auth/change-password/ \
#  -H "Content-Type: application/json" \
#  -H "Authorization: Bearer $tokenWorker" \
#  -d '{"current_password": "zg9o1im1LiJv", "new_password": "nueva456"}'

  curl -X POST http://localhost:8000/auth/reset-password/ \
  -H "Content-Type: application/json" \
  -d '{"email": "rogersantiagomh@ufps.edu.co"}'

#curl -X POST http://localhost:8000/auth/reset-password/confirm/ \
#  -H "Content-Type: application/json" \
#  -d '{"token": "uuid-del-correo", "new_password": "nueva456"}'
#
# Workers filtrados por manager (con token de manager)
# curl -X GET http://localhost:8000/workers/ \
#  -H "Authorization: Bearer TU_TOKEN_MANAGER"

#curl -X POST http://localhost:8000/auth/login/ \
#  -H "Content-Type: application/json" \
#  -d '{"email": "admin@gmail.com", "password": "admin1234"}'

#curl -X POST http://localhost:8000/auth/login/ \
#  -H "Content-Type: application/json" \
#  -d '{"email": "rogersantiagomh@ufps.edu.co", "password": "rMBL4zpoiK6a"}'

#curl -X POST http://localhost:8000/auth/login/ \
#  -H "Content-Type: application/json" \
#  -d '{"email": "jaiderricardocf@ufps.edu.co", "password": "zg9o1im1LiJv"}'

#curl -X POST http://localhost:8000/managers/ \
#  -H "Content-Type: application/json" \
#  -H "Authorization: Bearer $token" \
#  -d '{"name": "Roger", "lastname": "Miranda", "email": "rogersantiagomh@ufps.edu.co", "phone": "123456789"}'

#curl -X GET http://localhost:8000/managers/ \
#  -H "Authorization: Bearer $tokenAdmin"

#curl -X DELETE http://localhost:8000/managers/2/ \
#  -H "Authorization: Bearer $tokenAdmin"

#curl -X POST http://localhost:8000/workers/ \
#  -H "Content-Type: application/json" \
#  -H "Authorization: Bearer $tokenManager" \
#  -d '{"name": "Jaider", "lastname": "Contreras", "email": "jaiderricardocf@ufps.edu.co", "phone": "987654321"}'

#curl -X GET http://localhost:8000/workers/ \
#  -H "Authorization: Bearer $tokenManager"

#curl -X DELETE http://localhost:8000/workers/2/ \
#  -H "Authorization: Bearer $tokenAdmin"

#curl -X GET http://localhost:8000/users/me/ \
#  -H "Authorization: Bearer $tokenWorker"

#curl -X PATCH http://localhost:8000/users/me/ \
#  -H "Content-Type: application/json" \
#  -H "Authorization: Bearer $tokenWorker" \
#  -d '{"name": "Cacorro", "phone": "111222333"}'
