function change_side() {
    var url = window.location.pathname;
    var signup = document.getElementById("signup");
    var signin = document.getElementById("signin");
    if(url == "/signin"){
        signup.style.display = 'none';
    }
    else{
        signin.style.display = 'none'
    }
}
window.onload = change_side()