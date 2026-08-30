pipeline {
    agent {
        label 'dev'
    }

    environment {
        LLM_API_KEY = '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'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'master',
                    credentialsId: 'git_creds',
                    url: 'https://github.com/cloudops-lab/new-login-ai.git'
            }
        }

        stage('Build & Auto-Healing PR') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'git_creds', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PASS')]) {
                    sh '''#!/bin/bash
                        set -o pipefail

                        AUTH_REPO="https://${GIT_USER}:${GIT_PASS}@github.com/cloudops-lab/new-login-ai.git"
                        BRANCH_NAME="feature-ai-fix"

                        git config user.name "Chandandhani"
                        git config user.email "ai-agent@cloudops.internal"

                        # 1. Attempt initial build on master
                        if mvn1 clean install package 2>&1 | tee pipeline.log; then
                            echo "=== BUILD SUCCEEDED ==="
                        else
                            echo "=== BUILD FAILED: CREATING FIXED FEATURE BRANCH & PR ==="

                            # 2. Checkout feature branch from master
                            git checkout -B "${BRANCH_NAME}" origin/master

                            # 3. Patch pom.xml and call GitHub PR API directly from Python
                            export GIT_PASS="${GIT_PASS}"
                            python3 script/ai_agent_remediate.py pipeline.log

                            # 4. Commit and push the feature branch to GitHub
                            git add pom.xml
                            git commit -m "fix(ci): autonomous patch applied by AI agent" || echo "No diff to commit"
                            git push "${AUTH_REPO}" "${BRANCH_NAME}" --force
                            echo "=== PUSHED ${BRANCH_NAME} TO GITHUB ==="

                            exit 1
                        fi
                    '''
                }
            }
        }
    }

    post {
        always {
            cleanWs(deleteDirs: true, notFailBuild: true)
        }
    }
}
