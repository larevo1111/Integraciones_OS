import { boot } from 'quasar/wrappers'
import vue3GoogleLogin from 'vue3-google-login'
import { GOOGLE_CLIENT_ID } from 'src/config/oauth'

export default boot(({ app }) => {
  app.use(vue3GoogleLogin, {
    clientId: GOOGLE_CLIENT_ID
  })
})
