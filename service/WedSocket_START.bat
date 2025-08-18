@echo off
D:
cd D:\kors_group\portal
daphne -p 444 portal.asgi:application
