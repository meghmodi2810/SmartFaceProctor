(() => {
  'use strict';
  const forms = document.querySelectorAll('.needs-validation');

  Array.from(forms).forEach(form => {
    form.addEventListener('submit', event => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }

      const pass1 = document.getElementById("password1");
      const pass2 = document.getElementById("password2");

      if (pass1.value !== pass2.value) {
        pass2.setCustomValidity("Passwords do not match");
        event.preventDefault();
        event.stopPropagation();
      } else {
        pass2.setCustomValidity("");
      }

      form.classList.add('was-validated');
    }, false);
  });
})();

document.addEventListener('DOMContentLoaded', function() {
    const usernameInput = document.getElementById('username');
    const roleInput = document.getElementById('role');
    const form = document.querySelector('form');

    // Update role whenever username changes
    usernameInput.addEventListener('input', function() {
        const username = this.value.toUpperCase();
        if (username.startsWith('SPS')) {
            roleInput.value = 'Student';
        } else if (username.startsWith('SPF')) {
            roleInput.value = 'Faculty';
        } else {
            roleInput.value = '';
        }
    });

    // Form validation
    form.addEventListener('submit', function(event) {
        const username = usernameInput.value.toUpperCase();
        const password1 = document.getElementById('password1').value;
        const password2 = document.getElementById('password2').value;

        if (!roleInput.value) {
            event.preventDefault();
            alert('Invalid username format. Username must start with SPS for Student or SPF for Faculty.');
            return;
        }

        if (password1 !== password2) {
            event.preventDefault();
            alert('Passwords do not match.');
            return;
        }
    });
});
