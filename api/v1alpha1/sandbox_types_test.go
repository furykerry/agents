/*
Copyright 2026.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package v1alpha1

import (
	"testing"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func sandboxWithResume(pause *PausePolicy, resume *ResumePolicy) *Sandbox {
	if pause == nil && resume == nil {
		return &Sandbox{}
	}
	return &Sandbox{
		Spec: SandboxSpec{
			AutoPausePolicy: &AutoPausePolicy{
				Pause:  pause,
				Resume: resume,
			},
		},
	}
}

func TestWakeOnIngressTraffic(t *testing.T) {
	tests := []struct {
		name        string
		sandbox     *Sandbox
		wantEnabled bool
		wantTimeout time.Duration
	}{
		{
			name:        "nil sandbox",
			sandbox:     nil,
			wantEnabled: false,
		},
		{
			name:        "no auto-pause policy",
			sandbox:     &Sandbox{},
			wantEnabled: false,
		},
		{
			name:        "pause rule only",
			sandbox:     sandboxWithResume(&PausePolicy{WhenProbedIdleState: &ProbedIdleStateRule{Probe: "idle"}}, nil),
			wantEnabled: false,
		},
		{
			name:        "probed schedule rule only",
			sandbox:     sandboxWithResume(nil, &ResumePolicy{WhenProbedScheduleTime: &ProbedScheduleTimeRule{Probe: "sched"}}),
			wantEnabled: false,
		},
		{
			name:        "ingress traffic rule without pause timeout",
			sandbox:     sandboxWithResume(nil, &ResumePolicy{WhenIngressTraffic: &IngressTrafficRule{}}),
			wantEnabled: true,
		},
		{
			name: "ingress traffic rule with pause timeout",
			sandbox: sandboxWithResume(nil, &ResumePolicy{WhenIngressTraffic: &IngressTrafficRule{
				PauseTimeout: &metav1.Duration{Duration: 5 * time.Minute},
			}}),
			wantEnabled: true,
			wantTimeout: 5 * time.Minute,
		},
		{
			name: "ingress traffic rule with non-positive pause timeout",
			sandbox: sandboxWithResume(nil, &ResumePolicy{WhenIngressTraffic: &IngressTrafficRule{
				PauseTimeout: &metav1.Duration{Duration: -time.Second},
			}}),
			wantEnabled: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := WakeOnIngressTrafficEnabled(tt.sandbox); got != tt.wantEnabled {
				t.Errorf("WakeOnIngressTrafficEnabled() = %v, want %v", got, tt.wantEnabled)
			}
			if got := WakeOnIngressTrafficPauseTimeout(tt.sandbox); got != tt.wantTimeout {
				t.Errorf("WakeOnIngressTrafficPauseTimeout() = %v, want %v", got, tt.wantTimeout)
			}
		})
	}
}
