function checkPass()
{
    var pass1 = document.getElementById('password1');
    var pass2 = document.getElementById('password2');
    var message = document.getElementById('confirmMessage');
    var goodColor = "#66cc66";
    var badColor = "#ff6666";
    message.style.textAlign = "left";
    message.style.fontSize = "14px"
    if(pass1.value == pass2.value){
        message.style.color = goodColor;
        message.innerHTML = "passwords match!"
    }else{
        message.style.color = badColor;
        message.innerHTML = "passwords do not match! "
    }
}