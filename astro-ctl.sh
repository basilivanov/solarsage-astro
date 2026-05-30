#!/bin/bash
# SolarSage Astro - Quick Commands

case "$1" in
  status)
    echo "=== Production Server Status ==="
    sudo systemctl status solarsage-frontend --no-pager
    echo ""
    echo "=== Running Processes ==="
    ps aux | grep -E "next.*16.2.6" | grep -v grep
    ;;

  logs)
    echo "=== Production Server Logs ==="
    sudo journalctl -u solarsage-frontend -n 50 --no-pager
    ;;

  restart)
    echo "=== Restarting Production Server ==="
    sudo systemctl restart solarsage-frontend
    sleep 2
    sudo systemctl status solarsage-frontend --no-pager
    ;;

  build)
    echo "=== Building Production ==="
    cd /opt/solarsage-astro
    npm run build
    ;;

  deploy)
    echo "=== Building and Deploying ==="
    cd /opt/solarsage-astro
    npm run build && sudo systemctl restart solarsage-frontend
    sleep 2
    sudo systemctl status solarsage-frontend --no-pager
    ;;

  dev)
    echo "=== Switching to Dev Mode ==="
    sudo systemctl stop solarsage-frontend
    cd /opt/solarsage-astro
    npm run dev
    ;;

  prod)
    echo "=== Switching to Production Mode ==="
    pkill -f "next dev" 2>/dev/null || true
    sudo systemctl start solarsage-frontend
    sleep 2
    sudo systemctl status solarsage-frontend --no-pager
    ;;

  test)
    echo "=== Testing Production Endpoint ==="
    curl -s -o /dev/null -w "HTTP Status: %{http_code}\nTime: %{time_total}s\n" https://dev.astro.vasiliy-ivanov.ru/
    echo ""
    echo "=== Checking for HMR in HTML ==="
    curl -s https://dev.astro.vasiliy-ivanov.ru/ | grep -i "webpack\|hmr" || echo "✓ No HMR references (production mode)"
    ;;

  nginx)
    echo "=== Nginx Status ==="
    sudo nginx -t
    echo ""
    echo "=== Recent Nginx Errors ==="
    sudo tail -20 /var/log/nginx/error.log | grep "$(date +%Y/%m/%d)" || echo "No errors today"
    ;;

  *)
    echo "SolarSage Astro - Quick Commands"
    echo ""
    echo "Usage: $0 {command}"
    echo ""
    echo "Commands:"
    echo "  status   - Show production server status"
    echo "  logs     - Show production server logs"
    echo "  restart  - Restart production server"
    echo "  build    - Build production bundle"
    echo "  deploy   - Build and deploy (restart production)"
    echo "  dev      - Switch to dev mode"
    echo "  prod     - Switch to production mode"
    echo "  test     - Test production endpoint"
    echo "  nginx    - Check Nginx status and errors"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 deploy"
    echo "  $0 logs"
    ;;
esac
