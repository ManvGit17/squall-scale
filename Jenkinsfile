pipeline {
    agent any

    stages {

        stage('Unit tests') {
            steps {
                sh 'docker build --target test backend'
            }
        }

        stage('Build and deploy fleet') {
            steps {
                sh 'docker compose up -d --build'
            }
        }

        stage('Smoke test') {
            steps {
                // Reach the load balancer over the Compose network by service
                // name, so the check works whether or not the published port
                // is routable from the agent.
                sh 'docker run --rm --network squallscale curlimages/curl:8.11.1 -fsS http://lb/healthz | grep -q ok'
                sh 'docker run --rm --network squallscale curlimages/curl:8.11.1 -fsS http://lb/ | grep -q "Served by backend:"'
                sh 'docker run --rm --network squallscale curlimages/curl:8.11.1 -fsS http://lb/metrics | grep -q squallscale_requests_total'
            }
        }
    }

    post {
        always {
            sh 'docker compose down -v || true'
        }
        failure {
            echo 'Pipeline failed. Check console logs for errors.'
        }
    }
}
